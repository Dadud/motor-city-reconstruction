import unittest
from dataclasses import replace
from client.load_transfer import LoadTransferInput, transfer_load
from client.tire_response import f32


class LoadTransferTests(unittest.TestCase):
    def setUp(self):
        self.state = LoadTransferInput((2000, 2000, 1500, 1500), 0, 0, 0, 10,
                                       1450, 2.7, 1.6, 1.7, 0.55, 0.12, 0.18)

    def test_inclusive_attitude_and_strict_acceleration_gates(self):
        threshold = f32(0.1962)
        self.assertEqual(transfer_load(replace(self.state, longitudinal_acceleration=threshold)), self.state.loads)
        self.assertEqual(transfer_load(replace(self.state, lateral_acceleration=threshold)), self.state.loads)
        outside = replace(self.state, attitude=0.25001, longitudinal_acceleration=20)
        self.assertEqual(transfer_load(outside), self.state.loads)
        self.assertNotEqual(transfer_load(replace(outside, attitude=0.25)), self.state.loads)

    def test_longitudinal_direction_and_nonnegative_clamping(self):
        result = transfer_load(replace(self.state, longitudinal_acceleration=20))
        self.assertEqual(result[:2], (0, 0))
        self.assertGreater(result[2], self.state.loads[2])
        reverse = transfer_load(replace(self.state, longitudinal_acceleration=-20))
        self.assertGreater(reverse[0], self.state.loads[0])
        self.assertEqual(reverse[2:], (0, 0))

    def test_lateral_speed_gate_and_load_order(self):
        at_gate = replace(self.state, lateral_acceleration=5, speed=6)
        self.assertEqual(transfer_load(at_gate), self.state.loads)
        result = transfer_load(replace(at_gate, speed=6.001))
        self.assertGreater(result[0], self.state.loads[0])
        self.assertLess(result[1], self.state.loads[1])
        self.assertGreater(result[2], self.state.loads[2])
        self.assertLess(result[3], self.state.loads[3])
        self.assertAlmostEqual(sum(result), sum(self.state.loads), places=3)

    def test_invalid_observations(self):
        for changes in ({'loads': (1, 2, 3)}, {'loads': (-1, 1, 1, 1)},
                        {'front_track': 0}, {'mass': 0}, {'speed': float('inf')}):
            with self.assertRaises(ValueError):
                transfer_load(replace(self.state, **changes))


if __name__ == '__main__':
    unittest.main()
