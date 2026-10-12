import math
from types import SimpleNamespace
import unittest

from client.contact import Pose, WheelRig
from client.driving import Controls, Drive
from client.racing import TimeTrial
from client.track import RoadSlice


class Plane:
    def __init__(self, limit=10000, slope=0):
        self.limit, self.slope = limit, slope

    def lookup(self, x, z, **kwargs):
        return self if abs(x) <= self.limit and abs(z) <= self.limit else None

    def sample(self, x, z):
        size = math.sqrt(1+self.slope*self.slope)
        return z*self.slope, (0, 1/size, -self.slope/size)


def vehicle(terrain=None):
    rig = WheelRig(((-.7, 0, 1.3), (.7, 0, 1.3), (-.7, 0, -1.3), (.7, 0, -1.3)))
    radii = {k: .3 for k in ('LF', 'RF', 'LR', 'RR')}
    terrain = terrain or Plane()
    pose, contacts = rig.spawn_pose(terrain, Pose.yaw((0, 1, 0), 0), radii)
    return SimpleNamespace(rig=rig, radii=radii, terrain=terrain, pose=pose, contacts=contacts)


class DrivingTests(unittest.TestCase):
    def test_complete_sprint_freezes_result_until_reset(self):
        roads = tuple(RoadSlice((0, 0, z), (0, 1, 0), (0, 0, 1), (1, 0, 0), 5, 5)
                      for z in (0, 20, 40))
        trial = TimeTrial(SimpleNamespace(slices=roads))
        drive = Drive(vehicle(), trial)
        for _ in range(600):
            drive.update(1/60, Controls(throttle=1))
        self.assertTrue(trial.finished)
        self.assertEqual(drive.speed, 0)
        pose, elapsed = drive.pose, trial.elapsed
        drive.update(.1, Controls(throttle=1))
        self.assertEqual(drive.pose, pose)
        self.assertEqual(trial.elapsed, elapsed)
        drive.reset()
        self.assertFalse(trial.finished)

    def test_frame_rate_independence(self):
        a, b = Drive(vehicle()), Drive(vehicle())
        for _ in range(300):
            a.update(1/60, Controls(throttle=1, steering=.2))
        for _ in range(150):
            b.update(1/30, Controls(throttle=1, steering=.2))
        self.assertEqual(a.pose, b.pose)
        self.assertEqual(a.speed, b.speed)
        self.assertGreater(a.distance, 30)
        self.assertGreater(a.pose.position[0], 0)

    def test_braking_and_reverse(self):
        drive = Drive(vehicle())
        for _ in range(120):
            drive.update(1/60, Controls(throttle=1))
        forward = drive.pose.position[2]
        for _ in range(120):
            drive.update(1/60, Controls(brake=1))
        self.assertEqual(drive.speed, 0)
        for _ in range(180):
            drive.update(1/60, Controls(throttle=1, reverse=True))
        self.assertLess(drive.speed, 0)
        self.assertLess(drive.pose.position[2], forward)

    def test_missing_terrain_blocks_car(self):
        drive = Drive(vehicle(Plane(limit=3)))
        for _ in range(300):
            drive.update(1/60, Controls(throttle=1))
        self.assertTrue(drive.blocked)
        self.assertEqual(drive.speed, 0)
        self.assertLess(drive.pose.position[2], 1.71)
        self.assertTrue(all(c.gap is not None for c in drive.contacts))

    def test_bank_and_reset(self):
        drive = Drive(vehicle(Plane(slope=.1)))
        initial = drive.pose
        for _ in range(120):
            drive.update(1/60, Controls(throttle=1))
        self.assertGreater(drive.pose.position[1], initial.position[1])
        self.assertTrue(all(c.gap >= .02-1e-6 for c in drive.contacts))
        drive.reset()
        self.assertEqual(drive.pose, initial)
        self.assertEqual(drive.elapsed, 0)
        self.assertEqual(drive.distance, 0)

    def test_bounded_catchup_and_invalid_input(self):
        drive = Drive(vehicle())
        self.assertEqual(drive.update(10), 30)
        self.assertAlmostEqual(drive.elapsed, .25)
        for dt in (-1, float('nan')):
            with self.assertRaises(ValueError):
                drive.update(dt)
        for kwargs in ({'throttle': 2}, {'steering': float('nan')}, {'brake': -1}):
            with self.assertRaises(ValueError):
                Controls(**kwargs)
