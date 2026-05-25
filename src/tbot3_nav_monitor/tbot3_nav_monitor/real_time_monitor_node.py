import rclpy
from rclpy.node import Node

from nav2_msgs.action import NavigateToPose
# from nav2_msgs.action.navigate_to_pose import NavigateToPose_FeedbackMessage
from std_msgs.msg import Float32


class RealTimeMonitorNode(Node):

    def __init__(self):

        super().__init__('real_time_monitor_node')

        # ---------------- NAV2 FEEDBACK ----------------
        self.sub = self.create_subscription(
            NavigateToPose.Impl.FeedbackMessage,
            '/navigate_to_pose/_action/feedback',
            self.cb,
            10
        )

        # ---------------- BATTERY ----------------
        self.battery = 100.0

        self.create_subscription(
            Float32,
            '/battery_state',
            self.battery_cb,
            10
        )

        self.get_logger().info("Real Time Monitor Node started")

    # =========================================================
    # BATTERY CALLBACK
    # =========================================================

    def battery_cb(self, msg: Float32):

        self.battery = msg.data

    # =========================================================
    # NAV2 CALLBACK
    # =========================================================

    def cb(self, msg):

        fb = msg.feedback

        log_msg = (
            "\n==============================\n"
            f"ETA: {fb.estimated_time_remaining.sec}.{fb.estimated_time_remaining.nanosec:09d} s\n"
            f"Distance remaining: {fb.distance_remaining:.2f} m\n"
            f"Navigation time: {fb.navigation_time.sec}.{fb.navigation_time.nanosec:09d} s\n"
            f"Recoveries: {fb.number_of_recoveries}\n"
            f"Pose: x={fb.current_pose.pose.position.x:.2f}, y={fb.current_pose.pose.position.y:.2f}\n"
            f"Battery: {self.battery:.2f} %\n"
            "==============================\n"
        )
        self.get_logger().info(log_msg, throttle_duration_sec=0.5)

# =========================================================
# MAIN
# =========================================================

def main():
    rclpy.init()
    node = RealTimeMonitorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()