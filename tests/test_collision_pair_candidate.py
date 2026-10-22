import struct
import unittest

from client.body_geometry import body_samples
from client.collision_pair_candidate import (dynamic_pair_candidate,
                                             build_dynamic_candidate_table,
                                             resolve_dynamic_pair_retries)
from client.collision_pair_geometry import OrientedCollisionBox
from client.collision_pair_solver import CollisionPairBody


def owner(position=(0., 0., 0.), radius=.75):
    image = bytearray(0xDC)
    struct.pack_into('<3f', image, 8, *position)
    struct.pack_into('<f', image, 0xD8, radius)
    return image


def record(origin=(0., 0., 0.), local=(0., 0., 0.), radius=1.,
           active=True, matrix=(1., 0., 0., 0., 1., 0., 0., 0., 1.)):
    image = bytearray(0x78)
    struct.pack_into('<3f', image, 0, *origin)
    struct.pack_into('<9f', image, 0x0C, *matrix)
    struct.pack_into('<f', image, 0x30, float(active))
    struct.pack_into('<3f', image, 0x4C, *local)
    struct.pack_into('<f', image, 0x48, radius)
    struct.pack_into('<I', image, 0x74, int(active))
    return image


class DynamicPairCandidateTests(unittest.TestCase):
    @staticmethod
    def body(center, extents=(1., 1., 1.), mode=0):
        axes = ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.))
        vertices = tuple(value for point in body_samples(0, extents)
                         for value in point)
        return CollisionPairBody(
            OrientedCollisionBox(center, axes, extents), mode=mode,
            local_vertices=vertices)

    def test_transformed_center_and_inclusive_sphere_boundary(self):
        result = dynamic_pair_candidate(owner((1.75, 0., 0.)), record())
        self.assertEqual(result.center, (0., 0., 0.))
        self.assertEqual(result.radius, 1.75)
        self.assertTrue(result.within_radius)

    def test_candidate_center_uses_matrix_and_local_offset(self):
        matrix = (0., 0., 1., 0., 1., 0., -1., 0., 0.)
        result = dynamic_pair_candidate(
            owner((0., 0., 2.)), record(local=(2., 0., 0.), matrix=matrix))
        self.assertEqual(result.center, (0., 0., 2.))
        self.assertTrue(result.within_radius)

    def test_both_candidate_validity_words_gate_the_pair_test(self):
        no_type = record()
        struct.pack_into('<f', no_type, 0x30, -0.)
        no_validity = record()
        struct.pack_into('<f', no_validity, 0x74, -0.)
        for candidate in (no_type, no_validity):
            result = dynamic_pair_candidate(owner(), candidate)
            self.assertFalse(result.eligible)
            self.assertFalse(result.within_radius)

    def test_distance_outside_sphere_is_rejected(self):
        result = dynamic_pair_candidate(owner((1.751, 0., 0.)), record())
        self.assertFalse(result.within_radius)

    def test_retry_stops_after_separation_and_schedules_one_response(self):
        result = resolve_dynamic_pair_retries(
            self.body((.5, 0., 0.)), self.body((0., 0., 0.), (.4, .2, .1), mode=1))
        self.assertEqual((result.attempts, result.accepted_attempts), (2, 1))
        self.assertTrue(result.response_due)
        self.assertAlmostEqual(result.owner.box.center[0], 1.40625)

    def test_retry_caps_unresolved_coincident_pair_at_33_calls(self):
        result = resolve_dynamic_pair_retries(self.body((0., 0., 0.)),
                                              self.body((0., 0., 0.)))
        self.assertEqual((result.attempts, result.accepted_attempts), (33, 33))
        self.assertTrue(result.response_due)

    def test_first_rejection_does_not_schedule_response(self):
        result = resolve_dynamic_pair_retries(self.body((5., 0., 0.)),
                                              self.body((0., 0., 0.)))
        self.assertEqual((result.attempts, result.accepted_attempts), (1, 0))
        self.assertFalse(result.response_due)

    def test_dynamic_candidate_table_bounds_and_source_backlinks(self):
        source = bytearray(2 * 0x38)
        struct.pack_into('<H', source, 2, 0x23)
        struct.pack_into('<I', source, 8, 0x11111111)
        struct.pack_into('<I', source, 0x0c, 0x22222222)
        struct.pack_into('<I', source, 0x20, 0x33333333)
        struct.pack_into('<I', source, 0x24, 2)
        struct.pack_into('<I', source, 0x28, 0x71002000)
        struct.pack_into('<H', source, 0x38 + 2, 0x14)
        struct.pack_into('<I', source, 0x38 + 0x20, 0x44444444)
        vertices = struct.pack('<6f', -1., 2., 3., 3., 6., 7.)
        result = build_dynamic_candidate_table(
            bytes(source), {0x71002000: vertices}, source_address=0x71001000,
            table_address=0x71004000)
        active = result.records[:0x78]
        self.assertEqual(struct.unpack_from('<I', active, 0x30)[0], 0x22222222)
        self.assertEqual(struct.unpack_from('<I', active, 0x70)[0], 0x11111111)
        self.assertEqual(struct.unpack_from('<I', active, 0x74)[0], 0x33333333)
        self.assertEqual(struct.unpack_from('<3f', active, 0x4c), (1., 4., 5.))
        self.assertEqual(struct.unpack_from('<3f', active, 0x3c), (2., 2., 2.))
        self.assertAlmostEqual(struct.unpack_from('<f', active, 0x48)[0], 12 ** .5,
                               delta=1e-6)
        self.assertEqual(struct.unpack_from('<H', result.sources, 2)[0], 5)
        self.assertEqual(struct.unpack_from('<I', result.sources, 0x20)[0], 0x71004000)
        self.assertEqual(result.records[0x78:], bytes(0x78))
        self.assertEqual(struct.unpack_from('<H', result.sources, 0x38 + 2)[0], 0x14)


if __name__ == '__main__':
    unittest.main()
