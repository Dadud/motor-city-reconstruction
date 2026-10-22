import struct
import unittest

from client.body_constructor import construct_body
from client.collision_world_candidate import (CollisionWorldSample,
                                              decode_collision_world_sample,
                                              world_sample_overlaps_body)


def record(position=(0, 0, 0), vertical=0, kind=0):
    data = bytearray(0x14)
    struct.pack_into('<3i', data, 0, *position)
    struct.pack_into('<h', data, 0x0c, vertical)
    data[0x13] = kind
    return data


class CollisionWorldSampleTests(unittest.TestCase):
    def setUp(self):
        self.body = bytearray(construct_body(bytearray(0x2000), 0x1000, 1.,
                                             (1., 1., 1.), 0, 0))

    def test_all_packed_kinds_select_their_scale_and_radius(self):
        expected = ((0, 1., 3.), (1, .5, 12.),
                    (2, 2., 2.), (3, 1., 1.))
        for kind, vertical_scale, radius in expected:
            with self.subTest(kind=kind):
                value = decode_collision_world_sample(record(vertical=1024, kind=kind))
                self.assertEqual(value.kind, kind)
                self.assertAlmostEqual(value.vertical_value, vertical_scale * 4.)
                self.assertEqual(value.radius, radius)

    def test_coordinates_are_signed_16_16_values(self):
        value = decode_collision_world_sample(
            record((65536, -32768, -2147483648), kind=0))
        self.assertEqual(value.position, (1., -.5, -32768.))

    def test_kind_two_vertical_scaling_wraps_like_a_signed_word(self):
        value = decode_collision_world_sample(record(vertical=22499, kind=2))
        self.assertAlmostEqual(value.vertical_value, -80.2265625)

    def test_record_must_cover_the_complete_packed_sample(self):
        with self.assertRaises(ValueError):
            decode_collision_world_sample(bytes(0x13))

    def test_world_candidate_passes_radius_and_oriented_extent_gates(self):
        sample = CollisionWorldSample((0., 0., 0.), 1., 3., 0)
        self.assertTrue(world_sample_overlaps_body(self.body, sample))
        self.assertFalse(world_sample_overlaps_body(
            self.body, CollisionWorldSample((4., 0., 0.), 3., 3., 0)))

    def test_world_candidate_uses_strict_bounds(self):
        self.assertFalse(world_sample_overlaps_body(
            self.body, CollisionWorldSample((0., 0., 0.), 10., 0., 0)))
        self.assertFalse(world_sample_overlaps_body(
            self.body, CollisionWorldSample((4., 0., 0.), 3., 3., 0)))


if __name__ == '__main__':
    unittest.main()
