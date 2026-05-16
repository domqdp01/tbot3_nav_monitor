import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from nav_msgs.msg import OccupancyGrid
import numpy as np
import random

class ExplorerAvoidance(Node):
    def __init__(self):
        super().__init__('explorer_avoidance')

        # Velocity publisher
        self.cmd_vel_pub = self.create_publisher(
            Twist,
            '/cmd_vel',
            10
        )

        # Laser subscriber
        self.scan_subsc = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            10
        )

        
        # Timer
        self.timer = self.create_timer(0.1, self.control_loop)

        # Data
        self.scan_data = None
        self.min_dist =float('inf')
        self.ob_dect = False

        # Navigation params
        self.linear_vel = 0.22
        self.angular_vel = 0.4
        self.safe_dist = 0.2

        # State machine
        self.state = 'forward'        
        self.backup_target = 0.2
        self.backup_progress = 0.0
        self.turn_steps = 0
        self.turn_direction = 1

        self.get_logger().info('Autonomous Explorer Node Started!')
        self.get_logger().info('Robot is starting to explore and mapping the environment...')

    # -------------------------
    # LIDAR CALLBACK
    # -------------------------
    def scan_callback(self, msg):
        """Obstacle detection by LiDAR scan measurements"""
        self.scan_data = msg

        ranges = np.nan_to_num(
            np.array(msg.ranges),
            nan=msg.range_max,
            posinf=msg.range_max,
            neginf=0.0
        )

        self.min_dist = np.min(ranges)
        self.ob_dect = self.min_dist < self.safe_dist

    # -------------------------
    # CONTROL LOOP
    # -------------------------

    def control_loop(self):
        if self.scan_data is None:
            return
        
        twist = Twist()

        # =========================
        # STATE: FORWARD
        # =========================

        if self.state == "forward":
            self.get_logger().info("Exploring", throttle_duration_sec=3.0)
            if self.ob_dect:
                self.get_logger().info("Obstacle detected -> STOP")
                self.state = "stop"
                return
            
            twist.linear.x = self.linear_vel
            twist.angular.z = 0.0
        
        # =========================
        # STATE: STOP
        # =========================
        elif self.state == "stop":
            self.get_logger().info("Stopping robot", throttle_duration_sec=2.0)

            twist.linear.x = 0.0
            twist.angular.z = 0.0

            self.state = "backup"
            self.backup_progress = 0.0

        # =========================
        # STATE: BACKUP
        # =========================
        elif self.state == "backup":
            self.get_logger().info("Backing up", throttle_duration_sec=2.0)

            twist.linear.x = -0.1
            twist.angular.z = 0.0

            self.backup_progress += 0.1 * 0.1

            if self.backup_progress >= self.backup_target:
                self.state = "turn"

                ranges = np.nan_to_num(
                    np.array(self.scan_data.ranges),
                    nan = self.scan_data.range_max,
                    posinf= self.scan_data.range_max
                )

                mid = len(ranges) // 2
                left = np.mean(ranges[:mid])
                right = np.mean(ranges[mid:])

                if left > right:
                    self.turn_direction = 1
                    self.get_logger().info("Turning left", throttle_duration_sec=2.0)
                else:
                    self.turn_direction = -1
                    self.get_logger().info("Turning right", throttle_duration_sec=2.0)
                self.turn_steps = 0
        # =========================
        # STATE: TURN
        # =========================
        elif self.state == "turn":
            self.get_logger().info("Turning to avoid obstacle", throttle_duration_sec = 2.0)
            twist.linear.x = 0.0 
            twist.angular.z = self.turn_direction * self.angular_vel

            self.turn_steps +=1

            if self.turn_steps > 15:
                self.state = "forward"

        self.cmd_vel_pub.publish(twist)


    def shutdown(self):
        """Stop the robot when shutting down"""
        self.get_logger().info('Shutting down - Stopping robot...')
        twist = Twist()
        self.cmd_vel_pub.publish(twist)

def main(args=None):
    rclpy.init(args=args)
    node = ExplorerAvoidance()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()




        


            