import unittest

from client.track_cross_section import build_track_cross_section


class TrackMeshTests(unittest.TestCase):
    def test_builds_three_cross_section_points_and_turn_angle(self):
        transform = [0.0] * 14
        transform[5] = 1.0
        points, angle = build_track_cross_section(
            transform, (1, 0, 0), 0.25, 3.0,
            (0, 1, 0), (0, 0, 0), 2.0, 0.0)
        self.assertEqual(points, ((2.0, 0.25, 0.0),
                                  (2.0, 0.25, 0.0),
                                  (2.0, 0.25, 0.7853975296020508)))
        self.assertEqual(angle, 0.75)

    def test_rejects_angle_outside_verified_native_wrap_domain(self):
        transform = [0.0] * 14
        transform[5] = 1.0
        with self.assertRaises(ValueError):
            build_track_cross_section(transform, (1, 0, 0), 0, 0,
                                      (0, 1, 0), (0, 0, 0), 1, 0.5)

    def test_validates_native_vector_dimensions(self):
        with self.assertRaises(ValueError):
            build_track_cross_section([0] * 13, (1, 0, 0), 0, 1,
                                      (0, 1, 0), (0, 0, 0), 1, 0)


if __name__ == '__main__':
    unittest.main()
