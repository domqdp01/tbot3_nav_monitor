import rclpy
from rclpy.node import Node
import os
from std_msgs.msg import Int32
from std_msgs.msg import String
from rclpy.qos import QoSProfile, DurabilityPolicy
from nav2_msgs.action._navigate_to_pose import NavigateToPose_FeedbackMessage
from rcl_interfaces.srv import SetParameters
from rcl_interfaces.msg import Parameter, ParameterValue, ParameterType
from action_msgs.msg import GoalStatusArray



class AdaptiveBehaviorNode(Node):
    def __init__(self):
        super().__init__('adaptive_behavior_node')

        self.current_planner = "ThetaStar"
        self.current_level = -1

        # Subscriber recoveries
        self.recovery_sub = self.create_subscription(
            Int32,
            '/adaptive_nav/recovery_count',
            self.recovery_callback,
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

        self.status_sub = self.create_subscription(
            GoalStatusArray,
            '/navigate_to_pose/_action/status',
            self.status_callback,
            10
        )

        self.param_client = self.create_client(
            SetParameters,
            '/global_costmap/global_costmap/set_parameters'
        )

        self.local_param_client = self.create_client(
            SetParameters,
            '/local_costmap/local_costmap/set_parameters'
        )

        while not self.param_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn('Waiting for global costmap set_parameters service...')

        while not self.local_param_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn('Waiting for local costmap set_parameters service...')

        self.get_logger().info('Adaptive Behavior Node Started')

        # Initialize adaptive behavior at level 1
        init_msg = Int32()
        init_msg.data = 0

        self.recovery_callback(init_msg)
        self.last_recovery_time = self.get_clock().now()
        

    def recovery_callback(self, msg):

        recoveries = msg.data
        self.last_recovery_time = self.get_clock().now()

        # Planner Selector Policy
        if recoveries < 2:

            level = 1
            desired_planner = "ThetaStar"
            global_inflation = 0.55
            global_scaling = 3.0

            local_inflation = 0.35
            local_scaling = 4.0

        elif recoveries < 4:

            level = 2
            desired_planner = "GridBased"
            global_inflation = 0.75
            global_scaling = 2.0

            local_inflation = 0.50
            local_scaling = 3.0
        
        else:

            level = 3
            desired_planner = "GridBasedAStar"
            global_inflation = 0.9
            global_scaling = 1.2

            local_inflation = 0.6
            local_scaling = 2.5

        if level == self.current_level:
            return

        self.current_level = level

        # Publish at changes

        self.current_planner = desired_planner

        self.publish_planner(desired_planner)

        self.get_logger().warn(
            f'[ADAPTIVE] Planner -> {desired_planner}'
        )

        # GLOBAL COSTMAP

        self.set_costmap_param(
            self.param_client,
            "inflation_layer.inflation_radius",
            global_inflation
        )

        self.set_costmap_param(
            self.param_client,
            "inflation_layer.cost_scaling_factor",
            global_scaling
        )

        # LOCAL COSTMAP

        self.set_costmap_param(
            self.local_param_client,
            "inflation_layer.inflation_radius",
            local_inflation
        )

        self.set_costmap_param(
            self.local_param_client,
            "inflation_layer.cost_scaling_factor",
            local_scaling
        )

        self.get_logger().warn(
            f'[ADAPTIVE] Level {level} | '
            f'Planner={desired_planner} | '
            f'G_infl={global_inflation} G_scale={global_scaling} | '
            f'L_infl={local_inflation} L_scale={local_scaling}'
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
        future = client.call_async(request)


    def status_callback(self, msg):

        for status in msg.status_list:

            # SUCCEEDED
            if status.status == 4: 

                self.get_logger().warn('[ADAPTIVE] Goal reached -> RESET')

                self.last_recovery_time = self.get_clock().now()
                self.current_level = -1

                reset_msg = Int32()
                reset_msg.data = 0

                self.recovery_callback(reset_msg)
    

def main(args=None):

    rclpy.init(args=args)

    node = AdaptiveBehaviorNode()

    rclpy.spin(node)

    node.destroy_node()

    rclpy.shutdown()


if __name__ == '__main__':
    main()