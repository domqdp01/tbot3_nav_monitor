# tbot3_nav_monitor

# tbot3_nav_monitor

A ROS 2 (Humble) package for **adaptive navigation monitoring** of a TurtleBot3 Burger in Gazebo simulation. The system observes Nav2 recovery events in real time and automatically tunes planner, costmap inflation, velocity limits, and goal tolerances — logging all navigation metrics to CSV for post-run analysis.

---

## Overview

`tbot3_nav_monitor` extends the standard TurtleBot3 + Nav2 stack with a set of lightweight Python nodes that form a closed-loop adaptive system:

```
Nav2 feedback ──► RecoveryMonitorNode
                        │
                        ▼ /adaptive_nav/recovery_level (Int32)
          ┌─────────────┼──────────────────┐
          ▼             ▼                  ▼
AdaptiveBehaviorNode  VelocityAdapterNode  GoalToleranceAdapterNode
(planner + costmap)   (max_vel scaling)    (xy / yaw tolerance)
```

A `FakeBatteryNode` simulates battery drain based on distance travelled, while a `CSVLoggerNode` records all navigation telemetry to disk.

---

## Package Structure

```
tbot3_nav_monitor/
├── config/
│   ├── burger.yaml                        # Nav2 parameters (DWB, costmaps, …)
│   └── navigate_w_planner_selector.xml    # BehaviorTree with planner selector
├── launch/
│   ├── tbot3_full_nav.launch.py           # Full stack: Gazebo + Nav2 + CSV logger
│   └── adaptive_system.launch.py         # Adaptive nodes only
├── maps/
│   ├── house_map.yaml / house_map.pgm     # House world map
│   └── world_map.yaml / world_map.pgm    # TurtleBot3 world map
├── tbot3_nav_monitor/
│   ├── recovery_monitor_node.py
│   ├── adaptive_behavior_node.py
│   ├── velocity_adapter_node.py
│   ├── goal_tolerance_adapter_node.py
│   ├── real_time_monitor_node.py
│   ├── fake_battery_node.py
│   └── csv_logger_node.py
└── CSV_files/                             # Auto-created at runtime
```

Dependencies (third-party source packages in `src/`): `DynamixelSDK`, `turtlebot3_simulations`, `turtlebot3_msgs`.

---

## Nodes

### `recovery_monitor_node`
Subscribes to Nav2 action feedback and tracks the cumulative number of recovery behaviours. Publishes a recovery **level** (1–3) on `/adaptive_nav/recovery_level` whenever the level changes. Resets to level 1 when a goal is reached.

| Recoveries | Level |
|------------|-------|
| 0–1        | 1     |
| 2–3        | 2     |
| ≥ 4        | 3     |

**Published:** `/adaptive_nav/recovery_level` (`std_msgs/Int32`)

---

### `adaptive_behavior_node`
Listens on `/adaptive_nav/recovery_level` and adjusts the Nav2 global/local costmap inflation parameters and the active planner via dynamic parameter calls.

| Level | Planner        | Inflation radius | Cost scaling |
|-------|---------------|-----------------|--------------|
| 1     | ThetaStar     | 0.55            | 3.0          |
| 2     | ThetaStar     | 0.35            | 5.0          |
| 3     | GridBasedAStar | 0.15           | 8.0          |

**Published:** `/planner_selector` (`std_msgs/String`, transient-local QoS)

---

### `velocity_adapter_node`
Scales `FollowPath.max_vel_x` and `FollowPath.max_vel_theta` on the controller server according to the recovery level.

| Level | Scale | max\_vel\_x | max\_vel\_theta |
|-------|-------|------------|----------------|
| 1     | 100%  | 0.22       | 1.0            |
| 2     | 75%   | 0.165      | 0.75           |
| 3     | 50%   | 0.11       | 0.5            |

---

### `goal_tolerance_adapter_node`
Relaxes goal tolerances as the recovery level increases, giving the controller more freedom to declare the goal reached.

| Level | XY tolerance | Yaw tolerance |
|-------|-------------|--------------|
| 1     | 0.25 m      | 0.25 rad     |
| 2     | 0.45 m      | 0.35 rad     |
| 3     | 0.70 m      | 0.50 rad     |

---

### `real_time_monitor_node`
Prints a live telemetry panel to the terminal at 2 Hz, showing ETA (computed from current speed and remaining distance), distance remaining, navigation time, recovery count, robot pose, and battery level.

---

### `fake_battery_node`
Simulates a battery that drains linearly with distance travelled (100 % at 0 m, 0 % at 100 m). Publishes on `/battery_state` (`std_msgs/Float32`) every 0.5 s.

---

### `csv_logger_node`
Logs navigation telemetry row-by-row to a timestamped CSV file under `/workspace/tbot3_nav_monitor/CSV_files/`. Each row contains:

`time, x, y, vx, vz, eta, distance_remaining, recoveries, battery`

The file name includes the world name and a timestamp, e.g. `house_2025-05-25_23-14-00.csv`.

**Parameter:** `world_name` (string, default `unknown_world`)

---

## Topics Summary

| Topic | Type | Direction |
|-------|------|-----------|
| `/navigate_to_pose/_action/feedback` | Nav2 FeedbackMessage | subscribed |
| `/navigate_to_pose/_action/status` | `action_msgs/GoalStatusArray` | subscribed |
| `/cmd_vel` | `geometry_msgs/Twist` | subscribed |
| `/battery_state` | `std_msgs/Float32` | pub/sub |
| `/adaptive_nav/recovery_level` | `std_msgs/Int32` | pub/sub |
| `/planner_selector` | `std_msgs/String` | published |

---

## Requirements

- ROS 2 Humble
- Nav2 (`navigation2`, `nav2_bringup`)
- TurtleBot3 packages (`turtlebot3`, `turtlebot3_gazebo`, `turtlebot3_navigation2`)
- Gazebo (Classic)
- Python ≥ 3.10

Set the robot model before launching:

```bash
export TURTLEBOT3_MODEL=burger
```

---

## Build

```bash
cd /workspace/tbot3_nav_monitor
colcon build --symlink-install
source install/setup.bash
```

---

## Usage

### Full stack (Gazebo + Nav2 + CSV logger)

```bash
ros2 launch tbot3_nav_monitor tbot3_full_nav.launch.py
```

Optional arguments:

| Argument | Default | Description |
|----------|---------|-------------|
| `use_sim_time` | `true` | Use Gazebo clock |
| `map` | `maps/house_map.yaml` | Path to the map file |
| `world_name` | `house` | Label used in the CSV filename |

Example with a different map:

```bash
ros2 launch tbot3_nav_monitor tbot3_full_nav.launch.py \
  map:=/workspace/tbot3_nav_monitor/maps/world_map.yaml \
  world_name:=world
```

### Adaptive system only (if Nav2 is already running)

```bash
ros2 launch tbot3_nav_monitor adaptive_system.launch.py
```

This starts: `recovery_monitor_node`, `adaptive_behavior_node`, `velocity_adapter_node`, `goal_tolerance_adapter_node`, and `fake_battery_node`.

### Real-time monitor (standalone)

```bash
ros2 run tbot3_nav_monitor real_time_monitor_node
```

---

## Development Environment

The repository ships with a **Dev Container** (`.devcontainer/`). Open the folder in VS Code with the Remote Containers extension and the full ROS 2 Humble + Gazebo environment will be set up automatically via `post-create.sh` and `post-start.sh`.

---

## Maintainer

Domenico Quartodipalo — `domenico.quartodipalo@mail.polimi.com`