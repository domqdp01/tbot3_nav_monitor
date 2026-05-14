import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose 
from geometry_msgs.msg import PoseStamped
from action_msgs.msg import GoalStatus
import time


class NavigationGoalSender(Node):
    def __init__(self):
        super().__init__('navigation_goal_sender')

        self._action_client = ActionClient(
            self,
            NavigateToPose,
            'navigate_to_pose'
        )

        self.get_logger().info("Navigation Goal sender Started!")
        self.get_logger().info("Waiting for Nav2 action Server...")

        self._action_client.wait_for_server()
        self.get_logger().info('Nav2 ready!')

        self.goals = [
            {'x': 3.57, 'y': 1.05, 'yaw': 0.0},
            {'x': 2.0,  'y': -1.0,  'yaw': 0.0},
            {'x': 1.0,  'y': 0.0,  'yaw': 0.0},
        ]

        self.current_goal_index = 0

        self.send_next_goal()
        self._last_feedback_time = 0.0
    
    def send_next_goal(self):
        if self.current_goal_index < len(self.goals):
            goal = self.goals[self.current_goal_index]
            self.get_logger().info(
                f"Goal {self.current_goal_index + 1}/{len(self.goals)} "
                f"Going to -> x={goal['x']}, y={goal['y']}"
            )
            self.send_goal(**goal)
        else:
            self.get_logger().info("Goals completed, shutting down")

        

    def send_goal(self, x, y, yaw):
        goal_msg = NavigateToPose.Goal()

        goal_msg.pose = PoseStamped()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()

        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        goal_msg.pose.pose.position.z = 0.0

        goal_msg.pose.pose.orientation.x = 0.0
        goal_msg.pose.pose.orientation.y = 0.0
        goal_msg.pose.pose.orientation.z = 0.0
        goal_msg.pose.pose.orientation.w = 1.0

        # self.get_logger().info(f"Sending goal: x={x}, y = {y}")

        self._send_goal_future = self._action_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )

        self._send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Goal REJECTED by Nav2!')
            return
        self.get_logger().info('Goal ACCEPTED! Robot is moving...')
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.result_callback)

    def feedback_callback(self, feedback_msg):
        current_time = time.time()
        if current_time - self._last_feedback_time >= 1.5:
            pos = feedback_msg.feedback.current_pose.pose.position
            self.get_logger().info(f'Position: x={pos.x:.2f}, y={pos.y:.2f}')
            self._last_feedback_time = current_time

    def result_callback(self, future):
        result = future.result()
        if result.status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info('Goal REACHED! Robot stopped!')
            self.current_goal_index += 1
            self.send_next_goal()
        else:
            self.get_logger().error(f'Goal FAILED with Status: {result.status}')

def main(args=None):
    rclpy.init(args=args)
    node = NavigationGoalSender()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
