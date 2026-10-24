import struct
import unittest

from client.track_cross_section import (build_track_cross_section,
                                        build_track_grid_strips,
                                        wrap_track_turn)


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

    def test_cross_section_wraps_positive_angle_offsets(self):
        transform = [0.0] * 14
        transform[5] = 1.0
        _, angle = build_track_cross_section(transform, (1, 0, 0), 0, 0,
                                            (0, 1, 0), (0, 0, 0), 1, 0.5)
        self.assertEqual(angle, 0.25)

    def test_turn_wrapper_preserves_native_boundary_rules(self):
        self.assertEqual(wrap_track_turn(-3.2), 0.7999999523162842)
        self.assertEqual(wrap_track_turn(-2.0), 0.0)
        self.assertEqual(wrap_track_turn(1.0), 1.0)
        self.assertEqual(wrap_track_turn(2.0), 0.0)
        self.assertEqual(wrap_track_turn(3.2), 0.20000004768371582)
        self.assertEqual(struct.pack('<f', wrap_track_turn(-0.0)),
                         struct.pack('<f', -0.0))

    def test_validates_native_vector_dimensions(self):
        with self.assertRaises(ValueError):
            build_track_cross_section([0] * 13, (1, 0, 0), 0, 1,
                                      (0, 1, 0), (0, 0, 0), 1, 0)

    def test_grid_builder_emits_two_seventeen_point_strips(self):
        transform = [0.0] * 14
        transform[5] = 1.0
        centerline, outer, angle = build_track_grid_strips(
            transform, (1, 0, 0), 0.25, 3.0,
            (0, 1, 0), (0, 0, 0), 2.0, 0.0)
        self.assertEqual(len(centerline), 17)
        self.assertEqual(len(outer), 17)
        self.assertEqual(centerline[0], (2.0, 0.25, -6.283180236816406))
        self.assertEqual(centerline[-1], (2.0, 0.25, 6.283180236816406))
        self.assertEqual(outer[0], centerline[0])
        self.assertEqual(angle, 0.75)

    def test_grid_builder_uses_wrapped_angle_for_phase(self):
        transform = [0.0] * 14
        transform[5] = 1.0
        _, _, angle = build_track_grid_strips(transform, (1, 0, 0), 0, 1,
                                             (0, 1, 0), (0, 0, 0), 1, 0.5)
        self.assertEqual(angle, 0.25)


if __name__ == '__main__':
    unittest.main()
