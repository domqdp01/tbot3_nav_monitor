#!/bin/bash
set -e

echo "=========================================="
echo "Post-start: Building TurtleBot3 workspace"
echo "=========================================="

# Source ROS2 Humble
source /opt/ros/humble/setup.bash

# Detect architecture
ARCH=$(dpkg --print-architecture)
GAZEBO_AVAILABLE=false
if [ -f /etc/gazebo-status ]; then
    source /etc/gazebo-status
fi

# Navigate to workspace
cd /workspace/tbot3_nav_monitor

# Wait for filesystem
sleep 1

# Verify packages exist
PACKAGE_COUNT=$(find src/ -name "package.xml" 2>/dev/null | wc -l)

if [ "$PACKAGE_COUNT" -eq 0 ]; then
    # Try ls method for Windows mounts
    PACKAGE_COUNT=$(ls src/*/package.xml 2>/dev/null | wc -l)
fi

echo "Found $PACKAGE_COUNT ROS2 packages ($ARCH)"

if [ "$PACKAGE_COUNT" -eq 0 ]; then
    echo "[ERROR] No packages found!"
    echo "Something went wrong with post-create.sh"
    echo "The container may not work correctly."
    exit 1
fi

echo ""

# Check if already built
if [ -f "install/setup.bash" ]; then
    source install/setup.bash

    if ros2 pkg list | grep -q turtlebot3; then
        echo "[OK] Workspace already built"

        echo ""
        echo "=========================================="
        echo "[OK] TurtleBot3 Humble ready! ($ARCH)"
        echo "=========================================="
        echo ""
        echo "Quick start:"
        if [ "$GAZEBO_AVAILABLE" = "true" ]; then
            echo "  tb3_empty  - Launch empty world (Gazebo)"
        fi
        echo "  tb3_teleop - Keyboard control"
        echo "  VNC: http://localhost:6080 (password: ros)"
        echo "  Tip: Use a native VNC client on port 5901 for better performance"
        if [ "$GAZEBO_AVAILABLE" != "true" ]; then
            echo ""
            echo "  NOTE: Gazebo is not available on $ARCH."
            echo "  RViz, Nav2, SLAM, and teleop still work."
        fi
        echo "=========================================="
        exit 0
    fi
fi

# Build workspace with all available cores
echo "Building workspace... (first time: 2-3 minutes)"
echo ""

# Clean contents of build dirs (can't rm the dirs themselves — they're Docker volume mounts)
find build/ -mindepth 1 -delete 2>/dev/null || true
find install/ -mindepth 1 -delete 2>/dev/null || true
find log/ -mindepth 1 -delete 2>/dev/null || true

# On arm64 without Gazebo, skip simulation packages that would fail
COLCON_ARGS="--symlink-install --parallel-workers $(nproc) --cmake-args -DCMAKE_BUILD_TYPE=Release"

if [ "$GAZEBO_AVAILABLE" != "true" ]; then
    # Skip packages that depend on Gazebo (they won't build without it)
    COLCON_ARGS="$COLCON_ARGS --packages-skip turtlebot3_gazebo turtlebot3_fake_node turtlebot3_manipulation_gazebo"
fi

colcon build $COLCON_ARGS

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Build failed!"
    exit 1
fi

echo ""
echo "[OK] Build successful!"
source install/setup.bash

echo ""
echo "TurtleBot3 packages:"
ros2 pkg list | grep turtlebot3

echo ""
echo "=========================================="
echo "[OK] TurtleBot3 Humble ready! ($ARCH)"
echo "=========================================="
echo ""
echo "Quick start:"
if [ "$GAZEBO_AVAILABLE" = "true" ]; then
    echo "  tb3_empty  - Launch empty world (Gazebo)"
fi
echo "  tb3_teleop - Keyboard control"
echo "  VNC: http://localhost:6080 (password: ros)"
echo "  Tip: Use a native VNC client on port 5901 for better performance"
if [ "$GAZEBO_AVAILABLE" != "true" ]; then
    echo ""
    echo "  NOTE: Gazebo is not available on $ARCH."
    echo "  RViz, Nav2, SLAM, and teleop still work."
fi
echo "=========================================="