import struct
import unittest

from client.collision_pair_candidate import dynamic_pair_candidate


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


if __name__ == '__main__':
    unittest.main()
