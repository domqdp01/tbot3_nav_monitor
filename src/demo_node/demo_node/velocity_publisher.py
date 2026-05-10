import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

class VelocityPublisher(Node):
    def __init__(self):
        super().__init__('velocity_publisher')

        self.publisher = self.create_publisher(
            Twist,
            '/cmd_vel',
            10
        )

        # Publish every 5 seconds
        self.timer = self.create_timer(0.5, self.publish_velocity)
        self.get_logger().info('Velocity Publisher started! Publish to /cmd_vel')

    def publish_velocity(self):
        msg = Twist()
        msg.linear.x = 0.2
        msg.angular.z = 0.5

        self.publisher.publish(msg)
        self.get_logger().info(
            f'Publishing: linear.x = {msg.linear.x}, angular.z = {msg.angular.z}'
        )

def main(args=None):
    rclpy.init()
    node = VelocityPublisher()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
    