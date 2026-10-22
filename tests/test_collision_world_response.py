import struct
import unittest

from client.collision_impulse import CollisionInertia
from client.collision_pair_response import CollisionImpactBody
from client.collision_world_response import (extract_world_contact_points,
                                             apply_world_decision_two_contact_cache,
                                             resolve_world_vertex_contact)


IDENTITY = (1., 0., 0., 0., 1., 0., 0., 0., 1.)


def body():
    return CollisionImpactBody(
        0x71000000, (0., 0., 0.), (0., 0., 0.), (0., 0., 0.),
        (0., 0., 0.), CollisionInertia(.001, (.001, .001, .001),
                                       IDENTITY, IDENTITY), 1000.,
        contact_record=bytes(0x400))


class WorldVertexContactTests(unittest.TestCase):
    def test_decision_two_cache_uses_strict_counter_threshold(self):
        image = bytearray(0x400)
        struct.pack_into('<f', image, 0x50, 100.)
        struct.pack_into('<f', image, 0x0c, 7.)
        struct.pack_into('<f', image, 0x3b4, 2.)
        untouched = bytes(image)
        self.assertEqual(apply_world_decision_two_contact_cache(
            image, 2, 0x1a, (1., 2., 3.)), untouched)
        struct.pack_into('<f', image, 0x3b4, 2.001)
        result = apply_world_decision_two_contact_cache(
            image, 2, 0x1a, (1., 2., 3.))
        self.assertEqual(struct.unpack_from('<f', result, 0x3c8)[0], 1500.)
        self.assertEqual(struct.unpack_from('<I', result, 0x3f8)[0], 0x1a)
        self.assertEqual(struct.unpack_from('<3f', result, 0x3e8), (1., 7., 3.))
        self.assertEqual(struct.unpack_from('<I', result, 0x3f4)[0], 5)

    def test_extractor_uses_the_ordinary_22_point_buffer(self):
        image = bytearray(0x400)
        values = tuple(float(index) for index in range(66))
        struct.pack_into('<66f', image, 0xe0, *values)
        result = extract_world_contact_points(image)
        self.assertEqual(result.count, 22)
        self.assertEqual(result.vertices, values)

    def test_extractor_builds_compact_eight_point_set(self):
        image = bytearray(0x400)
        struct.pack_into('<h', image, 0x3bc, 0)
        struct.pack_into('<f', image, 0xc4, .8)
        values = tuple(float(index) for index in range(66))
        struct.pack_into('<66f', image, 0xe0, *values)
        result = extract_world_contact_points(image)
        self.assertEqual(result.count, 8)
        self.assertEqual(len(result.vertices), 24)

    def test_selects_deepest_vertex_and_pushes_cached_world_geometry(self):
        vertices = (-.1, 0., 0.) + (-2., 0., 0.) * 21
        result = resolve_world_vertex_contact(body(), vertices, (1., 0., 0.),
                                              (0., 0., 0.), .25, .45, .2)
        self.assertFalse(result.collided)
        self.assertEqual(result.selected_vertex, 1)
        self.assertEqual(result.penetration, -2.)
        self.assertEqual(result.body.position, (2., 0., 0.))
        self.assertEqual(struct.unpack_from('<3f', result.body.contact_record, 0x1e8),
                         (2., 0., 0.))

    def test_rejects_unobserved_point_counts(self):
        with self.assertRaises(ValueError):
            resolve_world_vertex_contact(body(), (0.,) * 9, (1., 0., 0.),
                                         (0., 0., 0.), .25, .45, .2)


if __name__ == '__main__':
    unittest.main()
