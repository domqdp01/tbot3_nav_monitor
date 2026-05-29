import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

from nav2_msgs.action import NavigateToPose
from std_msgs.msg import Float32, Int32


LEVEL_LABELS = {
    1: "NOMINAL",
    2: "DEGRADED",
    3: "CRITICAL",
}


class RealTimeMonitorNode(Node):

    def __init__(self):

        super().__init__('real_time_monitor_node')

        self.current_vx = 0.0
        self.eps = 0.05
        self.goal_eps = 0.25
        self.last_eta = 0.0
        self.recovery_level = 1

        # ---------------- VEL SUBSCRIPTION ----------------
        self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10
        )

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

        # ---------------- RECOVERY LEVEL ----------------
        self.create_subscription(
            Int32,
            '/adaptive_nav/recovery_level',
            self.recovery_level_cb,
            10
        )

        self.get_logger().info("Real Time Monitor Node started")

    def cmd_vel_callback(self, msg):
        self.current_vx = msg.linear.x

    def battery_cb(self, msg: Float32):
        self.battery = msg.data

    def recovery_level_cb(self, msg: Int32):
        self.recovery_level = msg.data

    # ----------------------------------
    # NAV2 CALLBACK
    # ----------------------------------

    def cb(self, msg):

        fb = msg.feedback

        dist = fb.distance_remaining
        vx = abs(self.current_vx)

        is_stopped = vx < self.eps
        is_close = dist < self.goal_eps

        if is_stopped and not is_close:
            eta = self.last_eta
        elif is_close:
            eta = 0.0
        else:
            if vx > self.eps:
                eta = dist / vx
            else:
                eta = self.last_eta

        if eta is None or not isinstance(eta, (int, float)):
            eta = self.last_eta

        self.last_eta = eta

        level = self.recovery_level
        label = LEVEL_LABELS.get(level, "UNKNOWN")

        log_msg = (
            "\n==============================\n"
            f"ETA: {self.last_eta:.2f} s\n"
            f"Distance remaining: {fb.distance_remaining:.2f} m\n"
            f"Navigation time: {fb.navigation_time.sec + fb.navigation_time.nanosec / 1e9:.2f} s\n"
            f"Recoveries: {fb.number_of_recoveries}\n"
            f"Recovery level: {level} ({label})\n"
            f"Battery: {self.battery:.2f} %\n"
            "==============================\n"
        )
        self.get_logger().info(log_msg, throttle_duration_sec=0.5)


# ----------------------------------
# MAIN
# ----------------------------------

def main():
    rclpy.init()
    node = RealTimeMonitorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()