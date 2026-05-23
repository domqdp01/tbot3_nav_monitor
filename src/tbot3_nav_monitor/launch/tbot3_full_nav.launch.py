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


def generate_launch_description():

    TURTLEBOT3_MODEL = os.environ.get("TURTLEBOT3_MODEL", "burger")

    tb3_gazebo_dir = get_package_share_directory("turtlebot3_gazebo")
    tb3_nav2_dir   = get_package_share_directory("turtlebot3_navigation2")

    map_file = "/workspace/tbot3_nav_monitor/maps/house_map.yaml"

    nav2_param_file = os.path.join(
        tb3_nav2_dir, "param", "humble", f"{TURTLEBOT3_MODEL}.yaml"
    )

    use_sim_time_arg = DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        description="Usa il tempo di simulazione",
    )
    map_arg = DeclareLaunchArgument(
        "map",
        default_value=map_file,
        description="Percorso del file yaml della mappa",
    )

    use_sim_time = LaunchConfiguration("use_sim_time")
    map_path     = LaunchConfiguration("map")

    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(tb3_gazebo_dir, "launch", "turtlebot3_house.launch.py")
        ),
        launch_arguments={"use_sim_time": use_sim_time}.items(),
    )

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

    return LaunchDescription([
        use_sim_time_arg,
        map_arg,
        gazebo_launch,
        nav2_delayed,
    ])