"""
Unit tests for tbot3_nav_monitor core logic.
Tests run without ROS or Gazebo using pytest.

Run with:
    cd /workspace/tbot3_nav_monitor
    python3 -m pytest src/tbot3_nav_monitor/test/test_core_logic.py -v
"""

import pytest
import math

# ─────────────────────────────────────────────
# Logic extracted from recovery_monitor_node.py
# ─────────────────────────────────────────────

def compute_level(recoveries: int) -> int:
    """Map cumulative recovery count to adaptive level (1–3)."""
    if recoveries < 2:
        return 1
    elif recoveries < 4:
        return 2
    else:
        return 3


# ─────────────────────────────────────────────
# Constants from velocity_adapter_node.py
# ─────────────────────────────────────────────

BASE_VEL_X = 0.22
BASE_VEL_THETA = 1.0

VELOCITY_LEVELS = {
    1: {'scale': 1.00, 'label': '100%'},
    2: {'scale': 0.75, 'label': '75%'},
    3: {'scale': 0.50, 'label': '50%'},
}

def compute_velocities(level: int) -> tuple:
    """Return (max_vel_x, max_vel_theta) for a given recovery level."""
    scale = VELOCITY_LEVELS[level]['scale']
    return round(BASE_VEL_X * scale, 4), round(BASE_VEL_THETA * scale, 4)


# ─────────────────────────────────────────────
# Constants from adaptive_behavior_node.py
# ─────────────────────────────────────────────

BEHAVIOR_LEVELS = {
    1: {'planner': 'ThetaStar',      'global_inflation': 0.55, 'global_scaling': 3.0,
                                      'local_inflation':  0.55, 'local_scaling':  3.0},
    2: {'planner': 'ThetaStar',      'global_inflation': 0.35, 'global_scaling': 5.0,
                                      'local_inflation':  0.35, 'local_scaling':  5.0},
    3: {'planner': 'GridBasedAStar', 'global_inflation': 0.15, 'global_scaling': 8.0,
                                      'local_inflation':  0.15, 'local_scaling':  8.0},
}

def get_behavior_config(level: int) -> dict:
    return BEHAVIOR_LEVELS[level]


# ─────────────────────────────────────────────
# Constants from goal_tolerance_adapter_node.py
# ─────────────────────────────────────────────

TOLERANCE_LEVELS = {
    1: {'xy_tol': 0.25, 'yaw_tol': 0.25},
    2: {'xy_tol': 0.45, 'yaw_tol': 0.35},
    3: {'xy_tol': 0.80, 'yaw_tol': 0.60},
}

def get_tolerances(level: int) -> tuple:
    """Return (xy_tolerance, yaw_tolerance) for a given recovery level."""
    cfg = TOLERANCE_LEVELS[level]
    return cfg['xy_tol'], cfg['yaw_tol']


# ─────────────────────────────────────────────
# Logic extracted from fake_battery_node.py
# ─────────────────────────────────────────────

def compute_battery(distance_travelled: float) -> float:
    """Linear battery model: 100% at 0 m, 0% at 100 m."""
    battery = 100.0 * (1.0 - distance_travelled / 100.0)
    return max(battery, 0.0)

def compute_distance(pose_a: tuple, pose_b: tuple) -> float:
    """Euclidean distance between two (x, y) poses."""
    dx = pose_b[0] - pose_a[0]
    dy = pose_b[1] - pose_a[1]
    return math.sqrt(dx * dx + dy * dy)


# ─────────────────────────────────────────────
# Logic extracted from real_time_monitor_node.py
# ─────────────────────────────────────────────

LEVEL_LABELS = {
    1: "NOMINAL",
    2: "DEGRADED",
    3: "CRITICAL",
}

def compute_eta(dist: float, vx: float, last_eta: float,
                eps: float = 0.05, goal_eps: float = 0.25) -> float:
    """Estimate time to goal based on current speed and distance."""
    is_stopped = abs(vx) < eps
    is_close = dist < goal_eps
    if is_close:
        return 0.0
    if is_stopped:
        return last_eta
    return dist / vx


# ═════════════════════════════════════════════
# TESTS
# ═════════════════════════════════════════════

# ─────────────────────────────────────────────
# RecoveryMonitorNode — compute_level
# ─────────────────────────────────────────────

class TestComputeLevel:

    def test_zero_recoveries_is_level_1(self):
        assert compute_level(0) == 1

    def test_one_recovery_is_level_1(self):
        assert compute_level(1) == 1

    def test_two_recoveries_is_level_2(self):
        assert compute_level(2) == 2

    def test_three_recoveries_is_level_2(self):
        assert compute_level(3) == 2

    def test_four_recoveries_is_level_3(self):
        assert compute_level(4) == 3

    def test_many_recoveries_is_level_3(self):
        assert compute_level(10) == 3

    def test_level_boundaries_are_correct(self):
        expected = {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3}
        for recoveries, expected_level in expected.items():
            assert compute_level(recoveries) == expected_level


# ─────────────────────────────────────────────
# VelocityAdapterNode — velocity scaling
# ─────────────────────────────────────────────

class TestComputeVelocities:

    def test_level_1_full_speed(self):
        vel_x, vel_theta = compute_velocities(1)
        assert vel_x == 0.22
        assert vel_theta == 1.0

    def test_level_2_75_percent(self):
        vel_x, vel_theta = compute_velocities(2)
        assert vel_x == 0.165
        assert vel_theta == 0.75

    def test_level_3_50_percent(self):
        vel_x, vel_theta = compute_velocities(3)
        assert vel_x == 0.11
        assert vel_theta == 0.5

    def test_higher_level_means_lower_velocity(self):
        vel_x_1, _ = compute_velocities(1)
        vel_x_2, _ = compute_velocities(2)
        vel_x_3, _ = compute_velocities(3)
        assert vel_x_1 > vel_x_2 > vel_x_3

    def test_invalid_level_raises_key_error(self):
        with pytest.raises(KeyError):
            compute_velocities(99)


# ─────────────────────────────────────────────
# AdaptiveBehaviorNode — planner and costmap config
# ─────────────────────────────────────────────

class TestAdaptiveBehavior:

    def test_level_1_uses_thetastar(self):
        assert get_behavior_config(1)['planner'] == 'ThetaStar'

    def test_level_2_uses_thetastar(self):
        assert get_behavior_config(2)['planner'] == 'ThetaStar'

    def test_level_3_switches_to_grid_based_astar(self):
        assert get_behavior_config(3)['planner'] == 'GridBasedAStar'

    def test_higher_level_reduces_inflation_radius(self):
        inf_1 = get_behavior_config(1)['global_inflation']
        inf_2 = get_behavior_config(2)['global_inflation']
        inf_3 = get_behavior_config(3)['global_inflation']
        assert inf_1 > inf_2 > inf_3

    def test_higher_level_increases_cost_scaling(self):
        scale_1 = get_behavior_config(1)['global_scaling']
        scale_2 = get_behavior_config(2)['global_scaling']
        scale_3 = get_behavior_config(3)['global_scaling']
        assert scale_1 < scale_2 < scale_3

    def test_global_and_local_params_are_consistent(self):
        for level in [1, 2, 3]:
            cfg = get_behavior_config(level)
            assert cfg['global_inflation'] == cfg['local_inflation']
            assert cfg['global_scaling'] == cfg['local_scaling']

    def test_invalid_level_raises_key_error(self):
        with pytest.raises(KeyError):
            get_behavior_config(99)


# ─────────────────────────────────────────────
# GoalToleranceAdapterNode — tolerance scaling
# ─────────────────────────────────────────────

class TestGoalTolerance:

    def test_level_1_tolerances(self):
        xy, yaw = get_tolerances(1)
        assert xy == 0.25
        assert yaw == 0.25

    def test_level_2_tolerances(self):
        xy, yaw = get_tolerances(2)
        assert xy == 0.45
        assert yaw == 0.35

    def test_level_3_tolerances(self):
        xy, yaw = get_tolerances(3)
        assert xy == 0.80
        assert yaw == 0.60

    def test_higher_level_relaxes_xy_tolerance(self):
        xy_1, _ = get_tolerances(1)
        xy_2, _ = get_tolerances(2)
        xy_3, _ = get_tolerances(3)
        assert xy_1 < xy_2 < xy_3

    def test_higher_level_relaxes_yaw_tolerance(self):
        _, yaw_1 = get_tolerances(1)
        _, yaw_2 = get_tolerances(2)
        _, yaw_3 = get_tolerances(3)
        assert yaw_1 < yaw_2 < yaw_3

    def test_invalid_level_raises_key_error(self):
        with pytest.raises(KeyError):
            get_tolerances(99)


# ─────────────────────────────────────────────
# FakeBatteryNode — battery model and distance
# ─────────────────────────────────────────────

class TestFakeBattery:

    def test_full_battery_at_zero_distance(self):
        assert compute_battery(0.0) == 100.0

    def test_half_battery_at_50m(self):
        assert compute_battery(50.0) == 50.0

    def test_empty_battery_at_100m(self):
        assert compute_battery(100.0) == 0.0

    def test_battery_does_not_go_negative(self):
        assert compute_battery(200.0) == 0.0

    def test_battery_decreases_with_distance(self):
        assert compute_battery(10.0) > compute_battery(50.0) > compute_battery(90.0)

    def test_distance_between_same_points_is_zero(self):
        assert compute_distance((1.0, 2.0), (1.0, 2.0)) == 0.0

    def test_distance_horizontal(self):
        assert compute_distance((0.0, 0.0), (3.0, 0.0)) == pytest.approx(3.0)

    def test_distance_diagonal(self):
        assert compute_distance((0.0, 0.0), (3.0, 4.0)) == pytest.approx(5.0)


# ─────────────────────────────────────────────
# RealTimeMonitorNode — ETA computation
# ─────────────────────────────────────────────

class TestEtaComputation:

    def test_eta_zero_when_close_to_goal(self):
        assert compute_eta(dist=0.1, vx=0.2, last_eta=5.0) == 0.0

    def test_eta_uses_last_when_stopped(self):
        assert compute_eta(dist=2.0, vx=0.0, last_eta=10.0) == 10.0

    def test_eta_computed_from_speed_and_distance(self):
        eta = compute_eta(dist=2.0, vx=0.5, last_eta=0.0)
        assert eta == pytest.approx(4.0)

    def test_eta_decreases_as_distance_decreases(self):
        eta_far  = compute_eta(dist=4.0, vx=0.5, last_eta=0.0)
        eta_near = compute_eta(dist=1.0, vx=0.5, last_eta=0.0)
        assert eta_far > eta_near

    def test_level_labels_are_correct(self):
        assert LEVEL_LABELS[1] == "NOMINAL"
        assert LEVEL_LABELS[2] == "DEGRADED"
        assert LEVEL_LABELS[3] == "CRITICAL"