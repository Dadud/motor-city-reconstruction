from types import SimpleNamespace
import unittest

from client.racing import Gate, TimeTrial
from client.track import RoadSlice


def road(z, forward=(0, 0, 1)):
    return RoadSlice((0, 0, z), (0, 1, 0), forward, (1, 0, 0), 5, 5)


class RacingTests(unittest.TestCase):
    def test_gate_rejects_wrong_direction_width_and_level(self):
        gate = Gate((0, 0, 10), (0, 0, 1), (1, 0, 0), 5, 5)
        self.assertEqual(gate.crossing_fraction((0, 1, 9), (0, 1, 11)), .5)
        for previous, current in (((0, 0, 11), (0, 0, 9)),
                                  ((6, 0, 9), (6, 0, 11)),
                                  ((0, 8, 9), (0, 8, 11))):
            self.assertIsNone(gate.crossing_fraction(previous, current))

    def test_sprint_requires_order_and_interpolates_finish(self):
        trial = TimeTrial(SimpleNamespace(slices=(road(0), road(20), road(40))))
        self.assertFalse(trial.closed)
        self.assertIsNone(trial.update((0, 1, 39), (0, 1, 41), 1))
        self.assertFalse(trial.finished)
        trial.update((0, 1, 19), (0, 1, 21), 1)
        self.assertEqual(trial.update((0, 1, 39), (0, 1, 41), 1), 2.5)
        self.assertTrue(trial.finished)
        self.assertEqual(trial.best, 2.5)
        self.assertIsNone(trial.update((0, 1, 39), (0, 1, 41), 1))
        trial.reset()
        self.assertFalse(trial.started)
        self.assertEqual(trial.completed, [])

    def test_closed_lap_and_stationary_clock(self):
        trial = TimeTrial(SimpleNamespace(slices=(road(0), road(20), road(0))))
        self.assertTrue(trial.closed)
        trial.update((0, 1, 0), (0, 1, 0), 1)
        self.assertEqual(trial.elapsed, 0)
        trial.update((0, 1, 19), (0, 1, 21), 1)
        self.assertEqual(trial.next_gate, 0)
        self.assertEqual(trial.update((0, 1, -1), (0, 1, 1), 1), 1.5)
        self.assertEqual(trial.next_gate, 1)
        self.assertEqual(trial.elapsed, .5)
        self.assertIn('Lap 2', trial.label())
