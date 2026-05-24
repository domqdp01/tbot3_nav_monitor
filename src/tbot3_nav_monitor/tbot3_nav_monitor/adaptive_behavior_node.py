import rclpy
from rclpy.node import Node

from std_msgs.msg import Int32
from std_msgs.msg import String
from rclpy.qos import QoSProfile, DurabilityPolicy


class AdaptiveBehaviorNode(Node):
    def __init__(self):
        super().__init__('adaptive_behavior_node')

        self.current_planner = "ThetaStar"

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

        self.get_logger().info('Adaptive Behavior Node Started')

        self.publish_planner("ThetaStar")

    def recovery_callback(self, msg):
        recoveries = msg.data

        # Planner Selector Policy
        if recoveries < 2:
            desired_planner = "ThetaStar"

        elif recoveries < 4:
            desired_planner = "GridBased"
        
        else:
            desired_planner = "GridBasedAStar"

        # Publish at changes

        if desired_planner != self.current_planner:
            
            self.current_planner = desired_planner
            
            self.publish_planner(desired_planner)

            self.get_logger().warn(
                f'[ADAPTIVE] Switching planner to: {desired_planner}'
            )

    def publish_planner(self, planner_name):

        msg = String()
        msg.data = planner_name
        self.planner_pub.publish(msg)

def main(args=None):

    rclpy.init(args=args)

    node = AdaptiveBehaviorNode()

    rclpy.spin(node)

    node.destroy_node()

    rclpy.shutdown()


if __name__ == '__main__':
    main()