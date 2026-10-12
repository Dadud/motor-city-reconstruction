import math
import unittest

from client.contact import Pose
from client.motion import advance_pose
from client.world import pose_matrix


class WorldTests(unittest.TestCase):
    def test_gpu_transform_matches_contact_pose_after_motion(self):
        pose = Pose.yaw((-705, 1.15, 644), math.pi-0.016)
        pose = advance_pose(pose, (2, 0, -5), (0.3, 0.7, 0.1), (0, 0.5, 0))
        matrix = pose_matrix(pose)
        for point in ((0, 0, 0), (-1, -0.5, 2), (1, -0.5, -2)):
            gpu = tuple(sum(matrix[j*4+i]*point[j] for j in range(3))+matrix[12+i]
                        for i in range(3))
            for actual, expected in zip(gpu, pose.transform(point)):
                self.assertAlmostEqual(actual, expected)
        self.assertEqual(tuple(matrix[i] for i in (3, 7, 11, 15)), (0, 0, 0, 1))
