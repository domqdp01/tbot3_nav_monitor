import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32, String
from rclpy.qos import QoSProfile, DurabilityPolicy
from rcl_interfaces.srv import SetParameters
from rcl_interfaces.msg import Parameter, ParameterValue, ParameterType


# Parameters per level
LEVELS = {
    1: {
        'planner':          'ThetaStar',
        'global_inflation': 0.55,
        'global_scaling':   3.0,
        'local_inflation':  0.55,
        'local_scaling':    3.0,
    },
    2: {
        'planner':          'ThetaStar',
        'global_inflation': 0.35,
        'global_scaling':   5.0,
        'local_inflation':  0.35,
        'local_scaling':    5.0,
    },
    3: {
        'planner':          'GridBasedAStar',
        'global_inflation': 0.15,
        'global_scaling':   8.0,
        'local_inflation':  0.15,
        'local_scaling':    8.0,
    },
}


class AdaptiveBehaviorNode(Node):
    def __init__(self):
        super().__init__('adaptive_behavior_node')

        self.current_level = -1

        # -------------------------
        # PUBLISHERS
        # -------------------------

        self.level_sub = self.create_subscription(
            Int32,
            '/adaptive_nav/recovery_level',
            self.level_callback,
            10
        )

        qos = QoSProfile(
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL
        )

        self.planner_pub = self.create_publisher(
            String,
            '/planner_selector',
            qos
        )

        self.param_client = self.create_client(
            SetParameters,
            '/global_costmap/global_costmap/set_parameters'
        )

        self.local_param_client = self.create_client(
            SetParameters,
            '/local_costmap/local_costmap/set_parameters'
        )

        # Waiting services to be ready

        while not self.param_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn('Waiting for global costmap set_parameters service...')

        while not self.local_param_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn('Waiting for local costmap set_parameters service...')

        self.get_logger().info('Adaptive Behavior Node Started')

        # Initialize at level 1
        self.apply_level(1)

    def level_callback(self, msg):
        self.apply_level(msg.data)

    def apply_level(self, level):

        if level == self.current_level:
            return

        if level not in LEVELS:
            self.get_logger().error(f'[ADAPTIVE] Unknown level: {level}')
            return

        self.current_level = level
        cfg = LEVELS[level]

        # Planner
        self.publish_planner(cfg['planner'])

        # Global costmap
        self.set_costmap_param(self.param_client,       'inflation_layer.inflation_radius',   cfg['global_inflation'])
        self.set_costmap_param(self.param_client,       'inflation_layer.cost_scaling_factor', cfg['global_scaling'])

        # Local costmap
        self.set_costmap_param(self.local_param_client, 'inflation_layer.inflation_radius',   cfg['local_inflation'])
        self.set_costmap_param(self.local_param_client, 'inflation_layer.cost_scaling_factor', cfg['local_scaling'])

        self.get_logger().warn(
            f'[ADAPTIVE] Level {level} | \n'
            f'Planner={cfg["planner"]} | \n'
            f'G_infl={cfg["global_inflation"]} G_scale={cfg["global_scaling"]} | \n'
            f'L_infl={cfg["local_inflation"]} L_scale={cfg["local_scaling"]}\n'
        )

    def publish_planner(self, planner_name):
        msg = String()
        msg.data = planner_name
        self.planner_pub.publish(msg)

    def set_costmap_param(self, client, name, value):
        request = SetParameters.Request()
        param = Parameter()
        param.name = name
        param.value = ParameterValue()
        param.value.type = ParameterType.PARAMETER_DOUBLE
        param.value.double_value = float(value)
        request.parameters.append(param)
        client.call_async(request)


def main(args=None):
    rclpy.init(args=args)
    node = AdaptiveBehaviorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()