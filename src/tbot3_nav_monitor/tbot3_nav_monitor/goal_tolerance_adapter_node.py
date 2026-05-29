import rclpy
from rclpy.node import Node

from std_msgs.msg import Int32

from rcl_interfaces.srv import SetParameters
from rcl_interfaces.msg import (
    Parameter,
    ParameterValue,
    ParameterType
)


LEVELS = {
    1: {'xy_tol': 0.25, 'yaw_tol': 0.25},
    2: {'xy_tol': 0.45, 'yaw_tol': 0.35},
    3: {'xy_tol': 0.80, 'yaw_tol': 0.60},
}


class GoalToleranceAdapterNode(Node):

    def __init__(self):

        super().__init__('goal_tolerance_adapter_node')

        self.current_level = -1

        # -------------------------
        # SUBSCRIBER
        # -------------------------

        self.level_sub = self.create_subscription(
            Int32,
            '/adaptive_nav/recovery_level',
            self.level_callback,
            10
        )

        # -------------------------
        # SERVER/CLIENT
        # -------------------------

        self.param_client = self.create_client(
            SetParameters,
            '/controller_server/set_parameters'
        )

        while not self.param_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn(
                'Waiting for controller_server/set_parameters...'
            )

        self.get_logger().info(
            'Goal Tolerance Adapter Node Started'
        )

        self.apply_level(1)

    def level_callback(self, msg):

        self.apply_level(msg.data)

    def apply_level(self, level):

        if level == self.current_level:
            return

        if level not in LEVELS:

            self.get_logger().error(
                f'Unknown level: {level}'
            )

            return

        self.current_level = level

        cfg = LEVELS[level]

        self.set_param(
            'general_goal_checker.xy_goal_tolerance',
            cfg['xy_tol']
        )

        self.set_param(
            'general_goal_checker.yaw_goal_tolerance',
            cfg['yaw_tol']
        )

        self.get_logger().warn(
            f'[GOAL TOLERANCE] '
            f'Level={level} | '
            f'XY={cfg["xy_tol"]} | '
            f'YAW={cfg["yaw_tol"]}'
        )

    def set_param(self, name, value):

        request = SetParameters.Request()
        param = Parameter()
        param.name = name
        param.value = ParameterValue()
        param.value.type = ParameterType.PARAMETER_DOUBLE
        param.value.double_value = float(value)

        request.parameters.append(param)
        self.param_client.call_async(request)


def main(args=None):

    rclpy.init(args=args)
    node = GoalToleranceAdapterNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()