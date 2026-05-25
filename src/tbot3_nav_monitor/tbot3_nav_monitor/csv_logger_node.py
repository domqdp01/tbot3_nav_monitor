import rclpy
from rclpy.node import Node

from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import Twist
from tf2_ros import Buffer, TransformListener
from std_msgs.msg import Float32

import csv
import os
from datetime import datetime


class CSVLoggerNode(Node):

    def __init__(self):

        super().__init__('csv_logger_node')

        # ---------------- STATE ----------------
        self.vx = 0.0
        self.vz = 0.0

        self.last_data = None

       # ---------------- WORLD NAME ----------------

        self.declare_parameter('world_name', 'unknown_world')

        self.world_name = self.get_parameter(
            'world_name'
        ).get_parameter_value().string_value

        # ---------------- CSV PATH ----------------

        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        file_name = f"{self.world_name}_{now}.csv"

        csv_dir = "/workspace/tbot3_nav_monitor/CSV_files"

        # create folder if it does not exist
        os.makedirs(csv_dir, exist_ok=True)

        self.file_path = os.path.join(csv_dir, file_name)

        # ---------------- CSV INIT ----------------
        self.csv_file = open(self.file_path, mode='w', newline='')
        self.writer = csv.writer(self.csv_file)

        self.writer.writerow([
            "time",
            "x",
            "y",
            "vx",
            "vz",
            "eta",
            "distance_remaining",
            "recoveries",
            "battery"
        ])

        # ---------------- TF ----------------
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # ---------------- SUBS ----------------

        self.create_subscription(
            NavigateToPose.Impl.FeedbackMessage,
            '/navigate_to_pose/_action/feedback',
            self.nav_cb,
            10
        )

        self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_cb,
            10
        )

        self.create_subscription(
            Float32,
            '/battery_state',
            self.battery_cb,
            10
        )

        self.get_logger().info(f"CSV Logger started -> {self.file_path}")

    # =========================================================
    # CMD VEL
    # =========================================================

    def cmd_vel_cb(self, msg: Twist):
        self.vx = msg.linear.x
        self.vz = msg.angular.z

    # =========================================================
    # TF ROBOT POSE
    # =========================================================

    def get_pose(self):

        try:
            t = self.tf_buffer.lookup_transform(
                'map',
                'base_link',
                rclpy.time.Time()
            )

            x = t.transform.translation.x
            y = t.transform.translation.y

            return x, y

        except Exception:
            return None

    # =========================================================
    # BATTERY
    # =========================================================
    #     
    def battery_cb(self, msg: Float32):
        self.battery = msg.data

    # =========================================================
    # NAV2 FEEDBACK
    # =========================================================

    def nav_cb(self, msg):

        fb = msg.feedback

        pose = self.get_pose()
        if pose is None:
            return

        x, y = pose

        eta = fb.estimated_time_remaining.sec + fb.estimated_time_remaining.nanosec * 1e-9
        dist = fb.distance_remaining
        rec = fb.number_of_recoveries

        battery = self.battery  

        row = [
            self.get_clock().now().nanoseconds * 1e-9,
            x,
            y,
            self.vx,
            self.vz,
            eta,
            dist,
            rec,
            battery
        ]

        self.writer.writerow(row)
        self.csv_file.flush()

    # =========================================================
    # CLEAN EXIT
    # =========================================================

    def destroy_node(self):
        self.csv_file.close()
        super().destroy_node()


def main():

    rclpy.init()
    node = CSVLoggerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()