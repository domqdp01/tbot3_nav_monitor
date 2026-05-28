import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    TURTLEBOT3_MODEL = os.environ.get("TURTLEBOT3_MODEL", "burger")

    tb3_gazebo_dir = get_package_share_directory("turtlebot3_gazebo")
    tb3_nav2_dir   = get_package_share_directory("turtlebot3_navigation2")
    pkg_gazebo_ros = get_package_share_directory("gazebo_ros")

    # =========================
    # YOUR CUSTOM WORLD PATH
    # =========================
    world_file      = "/workspace/tbot3_nav_monitor/world/room.world"
    map_file        = "/workspace/tbot3_nav_monitor/maps/room_map.yaml"
    nav2_param_file = "/workspace/tbot3_nav_monitor/src/tbot3_nav_monitor/config/burger.yaml"

    # -------------------------
    # LAUNCH ARGUMENTS
    # -------------------------
    use_sim_time_arg = DeclareLaunchArgument(
        "use_sim_time", default_value="true",
        description="Use simulation time",
    )
    map_arg = DeclareLaunchArgument(
        "map", default_value=map_file,
        description="YAML map path",
    )
    world_name_arg = DeclareLaunchArgument(
        "world_name", default_value="custom_world",
        description="Gazebo world name",
    )

    use_sim_time = LaunchConfiguration("use_sim_time")
    map_path     = LaunchConfiguration("map")
    world_name   = LaunchConfiguration("world_name")

    # -------------------------
    # GAZEBO — gzserver con il tuo world
    # -------------------------
    gzserver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, "launch", "gzserver.launch.py")
        ),
        launch_arguments={"world": world_file}.items(),
    )

    gzclient = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, "launch", "gzclient.launch.py")
        )
    )

    # -------------------------
    # ROBOT STATE PUBLISHER (pubblica i TF)
    # -------------------------
    robot_state_publisher = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(tb3_gazebo_dir, "launch", "robot_state_publisher.launch.py")
        ),
        launch_arguments={"use_sim_time": use_sim_time}.items(),
    )

    # -------------------------
    # SPAWN TURTLEBOT3
    # -------------------------
    spawn_turtlebot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(tb3_gazebo_dir, "launch", "spawn_turtlebot3.launch.py")
        ),
        launch_arguments={"x_pose": "0.0", "y_pose": "0.0"}.items(),
    )

    # -------------------------
    # NAV2 (delayed di 5s per dare tempo a Gazebo)
    # -------------------------
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(tb3_nav2_dir, "launch", "navigation2.launch.py")
        ),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "map":          map_path,
            "params_file":  nav2_param_file,
        }.items(),
    )
    nav2_delayed = TimerAction(period=5.0, actions=[nav2_launch])

    # -------------------------
    # CSV LOGGER NODE
    # -------------------------
    csv_logger_node = Node(
        package="tbot3_nav_monitor",
        executable="csv_logger_node",
        name="csv_logger_node",
        output="screen",
        parameters=[{
            "use_sim_time": use_sim_time,
            "world_name":   world_name,
        }],
    )

    # -------------------------
    # LAUNCH DESCRIPTION
    # -------------------------
    return LaunchDescription([
        use_sim_time_arg,
        map_arg,
        world_name_arg,
        gzserver,
        gzclient,
        robot_state_publisher,
        spawn_turtlebot,
        nav2_delayed,
        csv_logger_node,
    ])