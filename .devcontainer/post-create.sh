#!/bin/bash
set -e

echo "=========================================="
echo "Post-create: Setting up TurtleBot3 Humble"
echo "=========================================="

# Source ROS2 Humble
source /opt/ros/humble/setup.bash

# Detect architecture and GPU
ARCH=$(dpkg --print-architecture)
echo "[ARCH] Running on: $ARCH"

GAZEBO_AVAILABLE=false
if [ -f /etc/gazebo-status ]; then
    source /etc/gazebo-status
fi

GPU_AVAILABLE=false
if nvidia-smi &>/dev/null; then
    GPU_AVAILABLE=true
    echo "[GPU] NVIDIA GPU detected — hardware rendering enabled"
elif [ -e /dev/dri ]; then
    GPU_AVAILABLE=true
    echo "[GPU] DRI device detected — hardware rendering enabled"
else
    echo "[GPU] No GPU detected — using software rendering"
fi

# Setup bashrc for current user
cat >> ~/.bashrc << BASHRC_EOF

# ROS2 Humble setup
source /opt/ros/humble/setup.bash
if [ -f /workspace/tbot3_nav_monitor/install/setup.bash ]; then
    source /workspace/tbot3_nav_monitor/install/setup.bash
fi

# Environment variables
export ROS_DOMAIN_ID=30
export TURTLEBOT3_MODEL=burger
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export QT_QPA_PLATFORM=xcb

# --- GPU / Rendering detection ---
if nvidia-smi &>/dev/null || [ -e /dev/dri ]; then
    export LIBGL_ALWAYS_SOFTWARE=0
    unset GALLIUM_DRIVER
else
    export LIBGL_ALWAYS_SOFTWARE=1
    export GALLIUM_DRIVER=llvmpipe
fi

# --- Gazebo config (only if installed) ---
if command -v gzserver &>/dev/null; then
    export GAZEBO_PLUGIN_PATH=/opt/ros/humble/lib:\$GAZEBO_PLUGIN_PATH
    export GAZEBO_MODEL_PATH=/usr/share/gazebo-11/models:/opt/ros/humble/share:\$GAZEBO_MODEL_PATH
    export GAZEBO_MODEL_DATABASE_URI=""
    export GAZEBO_MASTER_URI=http://localhost:11345

    # Gazebo simulation aliases
    alias tb3_empty='ros2 launch turtlebot3_gazebo empty_world.launch.py'
    alias tb3_world='ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py'
    alias tb3_house='ros2 launch turtlebot3_gazebo turtlebot3_house.launch.py'
fi

# Common aliases (work on all platforms)
alias cb='cd /workspace/tbot3_nav_monitor && colcon build --symlink-install --parallel-workers $(nproc)'
alias sb='source /workspace/tbot3_nav_monitor/install/setup.bash'
alias tb3_teleop='ros2 run turtlebot3_teleop teleop_keyboard'
alias tb3_slam='ros2 launch turtlebot3_cartographer cartographer.launch.py use_sim_time:=True'
alias tb3_nav='ros2 launch turtlebot3_navigation2 navigation2.launch.py use_sim_time:=True map:=\$HOME/maps/my_map.yaml'

BASHRC_EOF

# Fix workspace permissions
sudo chown -R $(whoami):$(whoami) /workspace/tbot3_nav_monitor

# Create src directory if it doesn't exist
mkdir -p /workspace/tbot3_nav_monitor/src

# Navigate to workspace src
cd /workspace/tbot3_nav_monitor/src

# Check if repositories exist AND have content (not empty directories)
NEED_CLONE=false

if [ ! -d "turtlebot3" ]; then
    NEED_CLONE=true
    echo "TurtleBot3 directory not found"
elif [ ! -f "turtlebot3/turtlebot3/package.xml" ]; then
    NEED_CLONE=true
    echo "TurtleBot3 directory exists but is empty - will re-clone"
    rm -rf DynamixelSDK turtlebot3 turtlebot3_msgs turtlebot3_simulations
fi

if [ "$NEED_CLONE" = true ]; then
    echo "Cloning TurtleBot3 repositories..."

    # Clone in parallel with shallow depth for speed
    git clone -b humble --depth 1 https://github.com/ROBOTIS-GIT/DynamixelSDK.git &
    git clone -b humble --depth 1 https://github.com/ROBOTIS-GIT/turtlebot3_msgs.git &
    git clone -b humble --depth 1 https://github.com/ROBOTIS-GIT/turtlebot3.git &

    # Only clone simulations if Gazebo is available
    if [ "$GAZEBO_AVAILABLE" = "true" ]; then
        git clone -b humble --depth 1 https://github.com/ROBOTIS-GIT/turtlebot3_simulations.git &
    else
        echo "[SKIP] Skipping turtlebot3_simulations (Gazebo not available on $ARCH)"
    fi
    wait

    echo "[OK] Repositories cloned"
else
    echo "[OK] TurtleBot3 repositories already exist with content"
fi

# Verify we have package.xml files
cd /workspace/tbot3_nav_monitor
PACKAGE_COUNT=$(find src/ -name "package.xml" 2>/dev/null | wc -l)
echo "Verified $PACKAGE_COUNT package.xml files"

# Back to workspace root
cd /workspace/tbot3_nav_monitor

# Initialize rosdep if not already done
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    echo "Initializing rosdep..."
    sudo rosdep init || true
fi

# Update rosdep
echo "Updating rosdep..."
rosdep update

# Install dependencies
echo "Installing dependencies..."
rosdep install --from-paths src --ignore-src -r -y || true

# Create maps directory
mkdir -p ~/maps

# Create Gazebo performance config (only if Gazebo is installed)
if [ "$GAZEBO_AVAILABLE" = "true" ]; then
    mkdir -p ~/.gazebo
    cat > ~/.gazebo/gui.ini << 'GAZEBO_INI'
[geometry]
x=0
y=0
width=1280
height=720

[rendering]
shadows=false
ambient_occlusion=false
GAZEBO_INI
fi

echo ""
echo "=========================================="
echo "[OK] Post-create setup complete!"
echo ""
echo "  Architecture: $ARCH"
if [ "$GPU_AVAILABLE" = true ]; then
    echo "  Rendering:    HARDWARE GPU"
else
    echo "  Rendering:    SOFTWARE (llvmpipe)"
fi
if [ "$GAZEBO_AVAILABLE" = "true" ]; then
    echo "  Gazebo:       AVAILABLE (shadows off, optimized)"
else
    echo "  Gazebo:       NOT AVAILABLE (arm64 — no apt package)"
    echo "                RViz, Nav2, SLAM, teleop still work"
fi
echo "  VNC:          port 5901 (native) or 6080 (noVNC)"
echo "=========================================="