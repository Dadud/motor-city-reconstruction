import math
import unittest

from client.motion import advance_velocity, advance_pose, support_pose
from client.contact import Pose, WheelRig


class MotionTests(unittest.TestCase):
    def test_pose_translation_and_distinct_support_prediction(self):
        pose = Pose((0, 5, 0))
        predicted = support_pose(pose, (48, 0, 0))
        self.assertEqual(predicted.position, (1, 5, 0))
        for _ in range(64):
            pose = advance_pose(pose, (48, 0, 0), (0, 0, 0))
        self.assertEqual(pose.position, (48, 5, 0))
        self.assertEqual(predicted.rotation, pose.rotation)

    def test_rotation_preserves_center_of_mass_and_world_axis(self):
        pose = Pose.yaw((3, 4, 5), 0.7)
        com = (1, -0.2, 0.5)
        old = pose.transform(com)
        changed = advance_pose(pose, (4, 0, 0), (0, math.pi * 32, 0), com)
        expected = Pose.yaw((0, 0, 0), 0.7 + math.pi / 2)
        for i in range(3):
            self.assertAlmostEqual(changed.transform(com)[i], old[i] + (4/64 if i==0 else 0))
            for j in range(3):
                self.assertAlmostEqual(changed.rotation[i][j], expected.rotation[i][j])
        for _ in range(4096):
            pose = advance_pose(pose, (0, 0, 0), (0.2, 0.3, -0.1), com)
        for i in range(3):
            self.assertAlmostEqual(pose.transform(com)[i], old[i], places=9)

    def test_pose_invalid_input_rejected(self):
        with self.assertRaises(ValueError):
            advance_pose(Pose((0, 0, 0)), (0, 0, 0), (0, math.nan, 0))
        with self.assertRaises(ValueError):
            support_pose(Pose((0, 0, 0)), (0, math.inf, 0))

    def test_noncommuting_rotation_order(self):
        pose = advance_pose(Pose((0, 0, 0)), (0, 0, 0), (math.pi*32,)*3)
        expected = ((0, 0, 1), (0, 1, 0), (-1, 0, 0))
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(pose.rotation[i][j], expected[i][j])

    def test_one_second_constant_acceleration_and_wheel_motion(self):
        linear = angular = (0, 0, 0)
        for _ in range(32):
            linear = advance_velocity(linear, (0, -9.81, 2))
            angular = advance_velocity(angular, (1, 0, 0))
        self.assertAlmostEqual(linear[1], -9.81)
        self.assertEqual(linear[2], 2)
        rig = WheelRig(((-1, 0, 2), (1, 0, 2), (-1, 0, -2), (1, 0, -2)))
        wheels = rig.velocities(Pose((0, 0, 0)), linear, angular)
        self.assertAlmostEqual(wheels['LF'][1], -11.81)
        self.assertAlmostEqual(wheels['LR'][1], -7.81)

    def test_invalid_motion_and_overflow_rejected(self):
        for vector in [(0, 0), (0, math.inf, 0), (math.nan, 0, 0)]:
            with self.assertRaises(ValueError):
                advance_velocity(vector, (0, 0, 0))
            with self.assertRaises(ValueError):
                advance_velocity((0, 0, 0), vector)
        with self.assertRaisesRegex(ValueError, 'overflowed'):
            advance_velocity((1.79e308, 0, 0), (1.79e308, 0, 0))
