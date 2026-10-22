import struct
import unittest

from client.collision_pair_dispatch import dispatch_track_pairs, swept_pose
from client.track_surface_lookup import (TrackSurfaceMemory,
                                         TrackSurfaceWorld)
from tools.track_surface_cases import BASE, BLOCKS, GEOMETRY, PATH, fixture


class PairDispatchTests(unittest.TestCase):
    def test_swept_pose_keeps_linear_motion_and_com_rotation_coupled(self):
        body = bytearray(0x200)
        struct.pack_into('<3f', body, 8, 4., 5., 6.)
        struct.pack_into('<3f', body, 0x14, 32., -16., 8.)
        struct.pack_into('<3f', body, 0x38, 0., .25, 0.)
        struct.pack_into('<3f', body, 0x5c, 2., 0., 0.)
        struct.pack_into('<9f', body, 0x78, 1., 0., 0., 0., 1., 0., 0., 0., 1.)

        future_position, future_matrix = swept_pose(body)
        self.assertEqual(len(future_matrix), 9)
        old_com = (6., 5., 6.)
        new_com = tuple(sum((2., 0., 0.)[j] * future_matrix[j * 3 + i]
                            for j in range(3)) + future_position[i]
                        for i in range(3))
        for actual, expected in zip(new_com, (old_com[0] + 1.,
                                              old_com[1] - .5,
                                              old_com[2] + .25)):
            self.assertAlmostEqual(actual, expected, places=5)

    def test_disabled_dispatcher_leaves_body_and_world_untouched(self):
        body = bytearray(0x478)
        world = TrackSurfaceWorld(
            TrackSurfaceMemory(bytes(65536), bytes(0x6000), BASE),
            (0., 0.), (1., 1.), BLOCKS, PATH, 0, 0)
        result = dispatch_track_pairs(body, world)
        self.assertEqual(result.body_image, bytes(body))
        self.assertEqual((result.sampled_points, result.surface_queries,
                          result.responses), (0, 0, 0))


if __name__ == '__main__':
    unittest.main()
