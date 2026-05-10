import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry

class OdometrySubscriber(Node):
    def __init__(self):
        super().__init__('odometry_subscriber')

        self.subscription = self.create_subscription(
            Odometry,
            '/odom',
            self.odometry_callback,
            10
        )

        self.get_logger().info("Odometry Subscriber started! Listening to /odom")

    def odometry_callback(self, msg):
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        # z = msg.pose.pose.position.z

        vx = msg.twist.twist.linear.x
        vz = msg.twist.twist.angular.z

        self.get_logger().info(
            f'Position: x={x:.2f}, y={y:.2f} | Velocity: vx={vx:.2f}, vz={vz:.2f}'
        )

def main(args=None):
    rclpy.init(args=args)
    node = OdometrySubscriber()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()