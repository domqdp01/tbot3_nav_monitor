#!/usr/bin/env python3
 
import rclpy
from rclpy.node import Node
from nav2_msgs.msg import BehaviorTreeLog

RECOVERY_NODES = {'Spin', 'BackUp', 'Wait', 'ClearEntireCostmap',
                  'ClearLocalCostmap-Context', 'ClearGlobalCostmap-Context',
                  'ClearLocalCostmap-Subtree', 'ClearGlobalCostmap-Subtree'}

class AdaptiveBehaviorNode(Node):
    def __init__(self):
        super().__init__('adaptive_behavior_node')

        # Parameters to count recoveries
        self.count = 0
        
        # Subscribers
        self.create_subscription(BehaviorTreeLog, '/behavior_tree_log', self.cb, 10)
        self.get_logger().info('Recovery counter started')

    def cb(self, msg):
        for event in msg.event_log:
            if (event.node_name in RECOVERY_NODES and event.current_status == 'RUNNING'):
                self.count += 1
                self.get_logger().info(f"[RECOVERY #{self.count}: {event.node_name}]")

def main():
    rclpy.init()
    node = AdaptiveBehaviorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print("Shutting down the node... Bye!")
    
    rclpy.shutdown()

if __name__ == '__main__':
    main()