import unittest
from types import SimpleNamespace

from client.fce import Part
from client.track_object_animation import (apply_track_object_pose,
    evaluate_track_object_animation, quaternion_to_matrix)


class TrackObjectPoseTests(unittest.TestCase):
    def test_quaternion_matrix_matches_native_row_formula(self):
        matrix = quaternion_to_matrix((0., 0., 0.70710677, 0.70710677))
        self.assertAlmostEqual(matrix[0], 0., places=6)
        self.assertAlmostEqual(matrix[1], 1., places=6)
        self.assertAlmostEqual(matrix[3], -1., places=6)
        self.assertAlmostEqual(matrix[4], 0., places=6)
        self.assertAlmostEqual(matrix[8], 1., places=6)

    def test_animation_keeps_extended_fraction_until_stored_weights(self):
        import struct
        animation = bytearray(8 + 2 * 20)
        struct.pack_into('<HH', animation, 4, 2, 0)
        struct.pack_into('<3i', animation, 8, 441294, 492752, -341485)
        struct.pack_into('<4h', animation, 20, 13470, -6098, 12165, 11079)
        struct.pack_into('<3i', animation, 28, -425941, 316014, 54172)
        struct.pack_into('<4h', animation, 40, -11558, 1570, -11576, -10887)
        pose = evaluate_track_object_animation(animation, 93171)
        self.assertAlmostEqual(pose.translation[1], 6.1704888, places=6)

    def test_pose_rotates_vertices_and_normals_then_applies_translation(self):
        part = Part('animated', (0, 0, 0), ((1, 2, 3),), ((1, 0, 0),), ())
        # Native matrix storage is column-major. This maps (x,y,z) to
        # (-y,x,z), a positive quarter turn around the vertical axis.
        pose = SimpleNamespace(rotation=(0, 1, 0, -1, 0, 0, 0, 0, 1),
                               translation=(10, 20, 30))
        posed = apply_track_object_pose(part, pose)
        self.assertEqual(posed.vertices, ((8, 21, 33),))
        self.assertEqual(posed.normals, ((0, 1, 0),))
        self.assertEqual(posed.origin, (0.0, 0.0, 0.0))


if __name__ == '__main__':
    unittest.main()
