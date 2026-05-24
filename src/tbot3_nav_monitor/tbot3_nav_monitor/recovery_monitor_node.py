import rclpy
from rclpy.node import Node
from nav2_msgs.action._navigate_to_pose import NavigateToPose_FeedbackMessage
from std_msgs.msg import Int32


class RecoveryMonitorNode(Node):
    def __init__(self):
        super().__init__('recovery_monitor_node')

        self.total_recoveries = 0

        self.feedback_sub = self.create_subscription(
            NavigateToPose_FeedbackMessage,
            '/navigate_to_pose/_action/feedback',
            self.feedback_callback,
            10
        )

        self.recovery_pub = self.create_publisher(
            Int32,
            '/adaptive_nav/recovery_count',
            10
        )

        self.get_logger().info('Recovery monitor node started')
    
    def feedback_callback(self, msg):

        new_recoveries = msg.feedback.number_of_recoveries

        if new_recoveries != self.total_recoveries:

            self.total_recoveries = new_recoveries

            recovery_msg = Int32()
            recovery_msg.data = self.total_recoveries
            self.recovery_pub.publish(recovery_msg)
            
            self.get_logger().warn(
                f"[RECOVERY] Total: {self.total_recoveries}"
            )

def main(args=None):
    rclpy.init(args=args)
    node = RecoveryMonitorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()


        