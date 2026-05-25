import rclpy
from rclpy.node import Node

from tf2_ros import Buffer, TransformListener
from std_msgs.msg import Float32
import math


class FakeBatteryNode(Node):

    def __init__(self):

        super().__init__('fake_battery_node')

        # ---------------- STATE ----------------
        self.last_pose = None
        self.distance_travelled = 0.0

        self.battery = 100.0

        # ---------------- TF ----------------
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # ---------------- PUBLISHER ----------------
        self.battery_pub = self.create_publisher(
            Float32,
            '/battery_state',
            10
        )

        # ---------------- TIMER ----------------
        self.create_timer(0.5, self.update_battery)

        self.get_logger().info("Fake Battery Node started")

    # ---------------- ROBOT POSE ----------------

    def get_robot_pose(self):

        try:
            trans = self.tf_buffer.lookup_transform(
                'map',
                'base_link',
                rclpy.time.Time()
            )

            x = trans.transform.translation.x
            y = trans.transform.translation.y

            return x, y

        except Exception:
            return None

    # ---------------- DISTANCE ----------------

    def update_distance(self, pose):

        if self.last_pose is None:
            self.last_pose = pose
            return

        dx = pose[0] - self.last_pose[0]
        dy = pose[1] - self.last_pose[1]

        dist = math.sqrt(dx * dx + dy * dy)

        self.distance_travelled += dist
        self.last_pose = pose

    # ---------------- BATTERY MODEL ----------------

    def compute_battery(self):

        # Linear with the distance travelled - 100 m maximum
        battery = 100.0 * (1.0 - self.distance_travelled / 100.0)

        return max(battery, 0.0)

    # ---------------- LOOP ----------------

    def update_battery(self):

        pose = self.get_robot_pose()

        if pose is not None:
            self.update_distance(pose)

        self.battery = self.compute_battery()

        msg = Float32()
        msg.data = self.battery
        self.battery_pub.publish(msg)

        # self.get_logger().info(
        #     f"Battery: {self.battery:.2f}%"
        # )


def main():
    rclpy.init()
    node = FakeBatteryNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()