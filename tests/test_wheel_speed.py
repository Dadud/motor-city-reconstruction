import math
import unittest
from dataclasses import replace

from client.wheel_speed import WheelSpeedInput, WheelSpeedState, project_wheel_speeds


class WheelSpeedTests(unittest.TestCase):
    def state(self):
        return WheelSpeedState(tuple(WheelSpeedInput(0, True, i-1, 0.5) for i in range(4)),
                               0, 20, 0, 1.2, 1.5, 1.6, 1.7)

    def test_straight_motion_and_yaw_slot_order(self):
        state = self.state()
        self.assertEqual(project_wheel_speeds(state), (20,)*4)
        result = project_wheel_speeds(replace(state, yaw_rate_turns=0.3))
        self.assertGreater(result[0], 20)
        self.assertLess(result[1], 20)
        self.assertLess(result[2], 20)
        self.assertGreater(result[3], 20)

    def test_airborne_uses_spin_for_every_contact_mask(self):
        state = self.state()
        for mask in range(16):
            wheels = tuple(replace(w, contact=bool(mask & (1 << i))) for i, w in enumerate(state.wheels))
            result = project_wheel_speeds(replace(state, wheels=wheels))
            self.assertEqual(result, tuple(20 if w.contact else w.spin_value*w.spin_scale for w in wheels))

    def test_angle_projects_lateral_motion_and_reverse(self):
        state = self.state()
        wheels = tuple(replace(w, angle=0.5) for w in state.wheels)
        lateral = replace(state, wheels=wheels, lateral_velocity=7, longitudinal_velocity=0)
        for speed in project_wheel_speeds(lateral):
            self.assertAlmostEqual(speed, 7, places=5)
        reversed_state = replace(lateral, lateral_velocity=-7)
        for speed in project_wheel_speeds(reversed_state):
            self.assertAlmostEqual(speed, -7, places=5)

    def test_validation_precedes_airborne_branch(self):
        state = self.state()
        for invalid in (replace(state, wheels=state.wheels[:3]), replace(state, rear_track=0),
                        replace(state, lateral_velocity=math.nan), replace(state, yaw_rate_turns=1e100)):
            with self.assertRaises(ValueError):
                project_wheel_speeds(invalid)
        wheels = tuple(replace(w, contact=False, angle=math.inf) for w in state.wheels)
        with self.assertRaises(ValueError):
            project_wheel_speeds(replace(state, wheels=wheels))
