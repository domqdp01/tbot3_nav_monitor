import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32
from rcl_interfaces.srv import SetParameters
from rcl_interfaces.msg import Parameter, ParameterValue, ParameterType


# Base velocities (100%) from DWB config
BASE_VEL_X     = 0.22
BASE_VEL_THETA = 1.0

# Velocity scaling per level
LEVELS = {
    1: {'scale': 1.00, 'label': '100%'},
    2: {'scale': 0.75, 'label': '75%'},
    3: {'scale': 0.50, 'label': '50%'},
}


class VelocityAdapterNode(Node):
    def __init__(self):
        super().__init__('velocity_adapter_node')

        self.current_level = -1

        self.level_sub = self.create_subscription(
            Int32,
            '/adaptive_nav/recovery_level',
            self.level_callback,
            10
        )

        self.controller_param_client = self.create_client(
            SetParameters,
            '/controller_server/set_parameters'
        )

        while not self.controller_param_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn('Waiting for controller_server set_parameters service...')

        self.get_logger().info('Velocity Adapter Node Started')

        # Initialize at level 1
        self.apply_level(1)

    def level_callback(self, msg):
        self.apply_level(msg.data)

    def apply_level(self, level):

        if level == self.current_level:
            return

        if level not in LEVELS:
            self.get_logger().error(f'[VELOCITY] Unknown level: {level}')
            return

        self.current_level = level
        scale = LEVELS[level]['scale']
        label = LEVELS[level]['label']

        vel_x     = round(BASE_VEL_X     * scale, 4)
        vel_theta = round(BASE_VEL_THETA * scale, 4)

        # DWB uses FollowPath.max_vel_x and FollowPath.max_vel_theta
        # max_speed_xy == match max_vel_x
        self.set_param('FollowPath.max_vel_x',     vel_x)
        self.set_param('FollowPath.max_speed_xy',  vel_x)
        self.set_param('FollowPath.max_vel_theta',  vel_theta)

        self.get_logger().warn(
            f'[VELOCITY] Level {level} ({label}) | '
            f'max_vel_x={vel_x} max_vel_theta={vel_theta}'
        )

    def set_param(self, name, value):

        request = SetParameters.Request()

        param = Parameter()
        param.name = name
        param.value = ParameterValue()
        param.value.type = ParameterType.PARAMETER_DOUBLE
        param.value.double_value = float(value)

        request.parameters.append(param)
        self.controller_param_client.call_async(request)


def main(args=None):
    rclpy.init(args=args)
    node = VelocityAdapterNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()