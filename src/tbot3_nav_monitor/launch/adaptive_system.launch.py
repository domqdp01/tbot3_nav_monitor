import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():

    use_sim_time = LaunchConfiguration('use_sim_time')

    return LaunchDescription([

        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='using simulation time'
        ),

        # Recovery Monitor Node
        Node(
            package='tbot3_nav_monitor',
            executable='recovery_monitor_node',
            name='recovery_monitor_node',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time
            }]
        ),

        # Adaptive Behavior Node
        Node(
            package='tbot3_nav_monitor',
            executable='adaptive_behavior_node',
            name='adaptive_behavior_node',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time
            }]
        ),

        # Velocity Adapter Node
        Node(
            package='tbot3_nav_monitor',
            executable='velocity_adapter_node',
            name='velocity_adapter_node',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time
            }]
        ),

        # Goal Tolerance Adapter Node
        Node(
            package='tbot3_nav_monitor',
            executable='goal_tolerance_adapter_node',
            name='goal_tolerance_adapter_node',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time
            }]
        ),

        Node(
            package='tbot3_nav_monitor',
            executable='fake_battery_node',
            name='fake_battery_node',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time
            }]
        )


    ])