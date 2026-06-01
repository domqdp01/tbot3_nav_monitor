# Multi-arch base: works natively on amd64 (Intel/AMD) AND arm64 (Apple Silicon)
FROM ros:humble-ros-base

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble

# TARGETARCH is set automatically by Docker BuildKit (amd64 or arm64)
ARG TARGETARCH

# ---- Core packages (work on ALL architectures) ----
RUN apt-get update -o Acquire::Check-Valid-Until=false && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    # Build tools
    python3-pip \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-vcstool \
    python3-argcomplete \
    build-essential \
    git vim wget curl \
    bash-completion sudo \
    software-properties-common \
    gnupg lsb-release \
    locales \
    # Desktop GUI tools
    ros-${ROS_DISTRO}-rviz2 \
    ros-${ROS_DISTRO}-rqt \
    ros-${ROS_DISTRO}-rqt-common-plugins \
    # Navigation2 and SLAM
    ros-${ROS_DISTRO}-navigation2 \
    ros-${ROS_DISTRO}-nav2-bringup \
    ros-${ROS_DISTRO}-cartographer \
    ros-${ROS_DISTRO}-cartographer-ros \
    ros-${ROS_DISTRO}-rmw-cyclonedds-cpp \
    # Robot description and transforms
    ros-${ROS_DISTRO}-robot-state-publisher \
    ros-${ROS_DISTRO}-joint-state-publisher \
    ros-${ROS_DISTRO}-joint-state-publisher-gui \
    ros-${ROS_DISTRO}-xacro \
    ros-${ROS_DISTRO}-tf2-ros \
    ros-${ROS_DISTRO}-tf2-tools \
    # Turtlebot3 Packages
    ros-${ROS_DISTRO}-turtlebot3 \
    ros-${ROS_DISTRO}-turtlebot3-msgs \
    ros-${ROS_DISTRO}-turtlebot3-simulations \
    # Teleop
    ros-${ROS_DISTRO}-teleop-twist-keyboard \
    ros-${ROS_DISTRO}-teleop-twist-joy \
    # ros2_control (may not be available on all platforms)
    ros-${ROS_DISTRO}-controller-manager \
    ros-${ROS_DISTRO}-ros2-control \
    ros-${ROS_DISTRO}-ros2-controllers \
    # OpenGL / GPU support (harmless on systems without GPU)
    mesa-utils \
    libglx-mesa0 \
    libgl1-mesa-dri \
    mesa-vulkan-drivers \
    x11-apps \
    libglvnd0 libgl1 libglx0 libegl1 \
    && locale-gen en_US en_US.UTF-8 \
    && update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

# ---- Gazebo Classic 11 (amd64 ONLY — no arm64 packages exist) ----
RUN if [ "$TARGETARCH" = "amd64" ]; then \
        apt-get update && apt-get install -y --no-install-recommends \
        gazebo \
        ros-${ROS_DISTRO}-gazebo-ros-pkgs \
        ros-${ROS_DISTRO}-gazebo-ros \
        && rm -rf /var/lib/apt/lists/* \
        && echo "GAZEBO_AVAILABLE=true" > /etc/gazebo-status; \
    else \
        echo "INFO: Gazebo Classic 11 is not available for arm64 (Apple Silicon)." && \
        echo "      Simulation features will be unavailable. RViz, Nav2, SLAM still work." && \
        echo "GAZEBO_AVAILABLE=false" > /etc/gazebo-status; \
    fi

ENV LANG=en_US.UTF-8

# Python dependencies
RUN pip3 install --no-cache-dir setuptools numpy transforms3d

# Create workspace directory
RUN mkdir -p /workspace/tbot3_nav_monitor/src
WORKDIR /workspace/tbot3_nav_monitor

CMD ["/bin/bash"]