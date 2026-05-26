# tbot3_nav_monitor

A ROS 2 (Humble) package for **adaptive navigation monitoring** of a TurtleBot3 Burger in Gazebo simulation. The system observes Nav2 recovery events in real time and automatically tunes planner, costmap inflation, velocity limits, and goal tolerances — logging all navigation metrics to CSV for post-run analysis.

---

## Table of Contents

- [Overview](#overview)
- [Implementation Approach](#implementation-approach)
- [Package Structure](#package-structure)
- [Nodes](#nodes)
- [Topics Summary](#topics-summary)
- [Requirements](#requirements)
- [Setup & Installation](#setup--installation)
  - [Option A: Dev Container (VS Code)](#option-a-dev-container-vs-code)
  - [Option B: Docker Hub (direct pull)](#option-b-docker-hub-direct-pull)
- [Build](#build)
- [Usage](#usage)
- [Multi-Environment Testing](#multi-environment-testing)
- [Demo Video](#demo-video)
- [Maintainer](#maintainer)

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

## Implementation Approach

The core design goal was a **closed-loop adaptive system** that degrades gracefully when navigation gets difficult, rather than failing outright.

### Why adaptive behavior?

Standard Nav2 configurations are static: they work well in open spaces but struggle in cluttered environments where the robot may trigger many recovery behaviours (spin, backup, wait). Instead of tuning parameters by hand for each map, this package monitors recoveries at runtime and automatically shifts to safer configurations.

### How the closed-loop works

1. **Observe** — `RecoveryMonitorNode` counts cumulative recovery actions from Nav2 action feedback and maps them to three levels (1 = normal, 2 = cautious, 3 = emergency).
2. **Decide** — The level is published on `/adaptive_nav/recovery_level`. Three independent adapter nodes subscribe to it and each adjust a different dimension of the Nav2 stack:
   - `AdaptiveBehaviorNode` → global/local costmap inflation and active planner
   - `VelocityAdapterNode` → max linear and angular velocity
   - `GoalToleranceAdapterNode` → XY and yaw goal tolerances
3. **Reset** — When a goal is successfully reached, the monitor resets to level 1 for the next goal.

### Design choices

- **Dynamic parameter calls over restarts** — adapters use `AsyncParameterClient` to change Nav2 parameters at runtime with zero downtime.
- **Transient-local QoS on `/planner_selector`** — late-joining subscribers (e.g. after Nav2 restarts) still receive the last published planner choice.
- **Separation of concerns** — each adapter is an independent node, making it easy to add new adaptation dimensions (e.g. replanning frequency) without touching existing nodes.
- **CSV logging as a first-class feature** — every run produces a timestamped file, enabling post-run analysis without needing to replay bags.

---

## Package Structure

```
tbot3_nav_monitor/
├── config/
│   ├── burger.yaml                        # Nav2 parameters 
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

| Level | Planner         | Inflation radius | Cost scaling |
|-------|-----------------|-----------------|--------------|
| 1     | ThetaStar       | 0.55            | 3.0          |
| 2     | ThetaStar       | 0.35            | 5.0          |
| 3     | GridBasedAStar  | 0.15            | 8.0          |

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
Simulates a battery that drains linearly with distance travelled (100% at 0 m, 0% at 100 m). Publishes on `/battery_state` (`std_msgs/Float32`) every 0.5 s.

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
- Gazebo Classic 11
- Python ≥ 3.10

---

## Setup & Installation

> **Note on GPU / display:** Gazebo Classic requires a display server. On Windows with Docker Desktop (and on any system without GPU passthrough), X11 forwarding is not available. This package uses a **noVNC desktop** embedded in the container — access the full GUI from any browser at `http://localhost:6080`, no X11 or GPU required.

---

### Option A: Dev Container (VS Code)

This is the recommended approach. The Dev Container automatically sets up the entire ROS 2 Humble + Gazebo environment.

**Prerequisites**

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/macOS) or [Docker Engine](https://docs.docker.com/engine/install/) (Linux)
- [VS Code](https://code.visualstudio.com/)
- [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) for VS Code

**Resource allocation (important for Windows)**

Open Docker Desktop → Settings → Resources and set:
- CPUs: 6–8 cores
- Memory: 12–16 GB

**Steps**

1. Clone the repository and open it in VS Code:

```bash
git clone https://github.com/YOUR_USERNAME/tbot3_nav_monitor.git
cd tbot3_nav_monitor
code .
```

2. VS Code will detect `.devcontainer/` and show a popup — click **"Reopen in Container"**.  
   Alternatively: `F1` → *Dev Containers: Reopen in Container*.

3. First build takes **10–15 minutes** (downloads ROS 2, Gazebo, TurtleBot3 packages). Subsequent opens take ~30 seconds.

4. Once inside the container, open your browser and go to **http://localhost:6080** (password: `ros`) to access the Gazebo GUI.

5. In the VS Code terminal, proceed to [Build](#build) and [Usage](#usage).

> **GPU note:** The devcontainer uses `--gpus all` for NVIDIA acceleration. If you don't have an NVIDIA GPU (e.g. Windows + AMD, or macOS), open `.devcontainer/devcontainer.json` and comment out the `"runArgs"` line before opening the container. Software rendering will be used automatically via noVNC.

---

### Option B: Docker Hub (direct pull)

Use this option if you don't have VS Code or prefer a plain Docker workflow.

**Pull the image**

```bash
docker pull YOUR_DOCKERHUB_USERNAME/tbot3_nav_monitor:latest
```

**Run the container**

```bash
docker run -it --rm \
  -p 6080:6080 \
  -e TURTLEBOT3_MODEL=burger \
  -e DISPLAY=:1 \
  YOUR_DOCKERHUB_USERNAME/tbot3_nav_monitor:latest
```

> On Linux with NVIDIA GPU, add `--gpus all` to the command above for hardware acceleration.

**Access the GUI**

Open your browser at **http://localhost:6080** (password: `ros`).

**Push your own image (for contributors)**

```bash
# Build from the repo root
docker build -t YOUR_DOCKERHUB_USERNAME/tbot3_nav_monitor:latest .

# Push
docker login
docker push YOUR_DOCKERHUB_USERNAME/tbot3_nav_monitor:latest
```

---

## Build

Inside the container (either Dev Container or Docker), run:

```bash
export TURTLEBOT3_MODEL=burger

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

Example with the TurtleBot3 world map:

```bash
ros2 launch tbot3_nav_monitor tbot3_full_nav.launch.py \
  map:=/workspace/tbot3_nav_monitor/maps/world_map.yaml \
  world_name:=world
```

### Adaptive system only (if Nav2 is already running)

```bash
ros2 launch tbot3_nav_monitor adaptive_system.launch.py
```

Starts: `recovery_monitor_node`, `adaptive_behavior_node`, `velocity_adapter_node`, `goal_tolerance_adapter_node`, `fake_battery_node`.

### Real-time monitor (standalone)

```bash
ros2 run tbot3_nav_monitor real_time_monitor_node
```

---

## Multi-Environment Testing

### Test environment

| Property | Value |
|----------|-------|
| Host OS | Windows 11 + Docker Desktop |
| Docker Engine | 27.x (WSL2 backend) |
| Container base | ROS 2 Humble (Ubuntu 22.04) |
| Gazebo | Classic 11 |
| Display | noVNC (browser-based, `localhost:6080`) |
| GPU passthrough | ❌ Not available on Windows/AMD — software rendering |

### Results

| Test | Status | Notes |
|------|--------|-------|
| Container build (Dev Container) | ✅ | ~12 min first build |
| Gazebo Classic launch | ✅ | Via noVNC at `localhost:6080` |
| Full Nav2 stack | ✅ | `tbot3_full_nav.launch.py` |
| Adaptive recovery levels 1→2→3 | ✅ | Triggered by dense obstacle placement |
| Velocity scaling per level | ✅ | Confirmed via `/cmd_vel` topic echo |
| CSV logging | ✅ | Files written to `CSV_files/` |
| Real-time monitor node | ✅ | 2 Hz terminal panel |
| Fake battery drain | ✅ | Drains linearly with distance |

### Known limitations

- **No GPU passthrough on Windows**: Gazebo runs in software rendering mode through noVNC. Performance is acceptable but the simulation may run slower than on a native Linux machine with a dedicated GPU. The noVNC workaround provides full GUI access without any X11 configuration.
- **Apple Silicon (M1/M2/M3)**: Gazebo Classic 11 has no `arm64` packages for Ubuntu 22.04. The simulation nodes will not run on Apple Silicon; all other ROS 2 nodes (Nav2, SLAM, teleop) work normally.
- **AMD GPU on Linux**: Replace the `runArgs` in `.devcontainer/devcontainer.json` with `["--device", "/dev/dri:/dev/dri"]` for DRI passthrough.

### Analysis

The adaptive system behaved as designed across all tested scenarios. At recovery level 1 the robot navigated efficiently using ThetaStar with generous inflation. Triggering level 2 (2–3 recoveries) visibly reduced speed and tightened costmap inflation, helping the robot find paths through narrower gaps. At level 3 (≥ 4 recoveries) the switch to GridBasedAStar with minimal inflation allowed the robot to plan through very tight passages that ThetaStar could not solve, at the cost of reduced speed and relaxed goal tolerances. The CSV logs confirmed that recovery counts, velocity adjustments, and position data were all recorded correctly throughout.

---

## Demo Video

> 🎬 **Coming soon** — a 5-minute walkthrough showing the full adaptive system in action (Gazebo launch → goal setting → recovery escalation → CSV output).

<!-- Once recorded, replace this section with:
[![Demo Video](https://img.youtube.com/vi/YOUR_VIDEO_ID/0.jpg)](https://youtu.be/YOUR_VIDEO_ID)
or embed directly if uploading to GitHub:
https://github.com/YOUR_USERNAME/tbot3_nav_monitor/assets/YOUR_VIDEO.mp4
-->

---

## Maintainer

Domenico Quarto di Palo — `quartodomenico0@gmail.com`