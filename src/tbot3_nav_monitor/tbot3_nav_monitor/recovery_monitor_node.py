import rclpy
from rclpy.node import Node
from nav2_msgs.action._navigate_to_pose import NavigateToPose_FeedbackMessage
from std_msgs.msg import Int32
from action_msgs.msg import GoalStatusArray


class RecoveryMonitorNode(Node):
    def __init__(self):
        super().__init__('recovery_monitor_node')

        self.total_recoveries = 0
        self.current_level = -1

        self.feedback_sub = self.create_subscription(
            NavigateToPose_FeedbackMessage,
            '/navigate_to_pose/_action/feedback',
            self.feedback_callback,
            10
        )

        self.level_pub = self.create_publisher(
            Int32,
            '/adaptive_nav/recovery_level',
            10
        )

        self.status_sub = self.create_subscription(
            GoalStatusArray,
            '/navigate_to_pose/_action/status',
            self.status_callback,
            10
        )

        self.get_logger().info('Recovery monitor node started')

    def compute_level(self, recoveries):
        if recoveries < 2:
            return 1
        elif recoveries < 4:
            return 2
        else:
            return 3

    def feedback_callback(self, msg):

        new_recoveries = msg.feedback.number_of_recoveries

        if new_recoveries == self.total_recoveries:
            return

        self.total_recoveries = new_recoveries
        level = self.compute_level(self.total_recoveries)

        self.get_logger().warn(
            f'[RECOVERY] Total: {self.total_recoveries} -> Level: {level}'
        )

        if level == self.current_level:
            return

        self.current_level = level
        self.publish_level(level)

    def publish_level(self, level):
        msg = Int32()
        msg.data = level
        self.level_pub.publish(msg)

    def status_callback(self, msg):

        for status in msg.status_list:

            if status.status == 4:  # SUCCEEDED

                self.get_logger().warn('[RECOVERY MONITOR] Goal reached -> reset')

                self.total_recoveries = 0
                self.current_level = 1

                self.publish_level(1)


def main(args=None):
    rclpy.init(args=args)
    node = RecoveryMonitorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()