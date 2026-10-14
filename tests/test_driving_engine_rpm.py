from dataclasses import replace
import unittest
from client.driving_engine_rpm import DrivingEngineRPM, update_driving_engine_rpm


class DrivingEngineRPMTests(unittest.TestCase):
    def setUp(self):
        self.state = DrivingEngineRPM(600, 7000, .5, .4, 2000, True,
                                     .7, 100, 300, 3000, 6800, 1, 175, 30)

    def test_disabled_engine_still_updates_target_but_stops_rotation(self):
        out = update_driving_engine_rpm(replace(self.state, enabled=False), 600)
        self.assertGreater(out.target_rpm, self.state.target_rpm)
        self.assertEqual((out.rpm, out.angular_speed, out.acceleration_output), (0, 0, 0))

    def test_neutral_does_not_couple_road_speed(self):
        slow = update_driving_engine_rpm(self.state, 600)
        fast = update_driving_engine_rpm(replace(self.state, longitudinal_speed=1000), 600)
        self.assertEqual(slow, replace(fast, longitudinal_speed=self.state.longitudinal_speed))

    def test_engaged_gear_couples_reverse_speed_magnitude(self):
        forward = update_driving_engine_rpm(replace(self.state, gear_index=2), 600)
        reverse = update_driving_engine_rpm(replace(self.state, gear_index=2, longitudinal_speed=-30), 600)
        self.assertEqual(forward.target_rpm, reverse.target_rpm)
        self.assertGreater(forward.target_rpm, 5000)

    def test_final_caller_clamp_overrides_idle_setting(self):
        out = update_driving_engine_rpm(replace(self.state, angular_speed=0, rpm=0,
                                              acceleration_input=0), 900)
        self.assertEqual(out.rpm, 900)

    def test_nonfinite_input_rejected(self):
        with self.assertRaises(ValueError):
            update_driving_engine_rpm(replace(self.state, normalized_rpm=float('nan')), 600)
