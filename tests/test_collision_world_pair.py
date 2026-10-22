import struct
import unittest

from client.body_constructor import construct_body
from client.collision_world_pair import resolve_world_decision_minus_one


OWNER = 0x71008000
TEMPORARY = 0x72006B24


def owner_body(velocity):
    image = bytearray(construct_body(bytes(0x2000), OWNER, 1000.,
                                     (1., 1., 1.), 0, 2))
    struct.pack_into('<3f', image, 8, 0., 0., 0.)
    struct.pack_into('<3f', image, 0x14, velocity, 0., 0.)
    struct.pack_into('<f', image, 0x3b4, 1.5)
    return image


class WorldPairTests(unittest.TestCase):
    def test_decision_minus_one_builds_proxy_and_applies_pair_cache(self):
        result = resolve_world_decision_minus_one(
            owner_body(1.), (.1, 0., 0.), .78125, 0x19, OWNER, TEMPORARY,
            .8, .7)

        self.assertTrue(result.collided)
        self.assertEqual(result.temporary_body_image[:4], b'\xfd\xff\xff\xff')
        self.assertEqual(struct.unpack_from('<f', result.temporary_body_image, 0x50)[0],
                         25.)
        self.assertEqual(struct.unpack_from('<3f', result.temporary_body_image, 0xcc),
                         (.78125, 3., .78125))
        self.assertAlmostEqual(
            struct.unpack_from('<3f', result.temporary_body_image, 8)[0], .1)
        self.assertAlmostEqual(result.contact_point[0], .1)
        self.assertEqual(result.contact_point[1:], (0., 0.))
        self.assertEqual(result.normal, (-1., 0., 0.))
        self.assertEqual(struct.unpack_from('<I', result.body_image, 0x3c4)[0], 0)
        self.assertEqual(struct.unpack_from('<I', result.body_image, 0x3f4)[0], 5)
        self.assertEqual(struct.unpack_from('<I', result.body_image, 0x3f8)[0], 0x19)
        self.assertAlmostEqual(struct.unpack_from('<f', result.body_image, 0x3c8)[0],
                               (1.5 * .14913242 + 5.) * 1000., delta=.001)

    def test_receding_pair_does_not_write_world_contact_cache(self):
        image = owner_body(-1.)
        result = resolve_world_decision_minus_one(
            image, (.1, 0., 0.), .78125, 0x19, OWNER, TEMPORARY, .8, .7)

        self.assertFalse(result.collided)
        self.assertEqual(result.body_image, bytes(image))

    def test_zero_horizontal_separation_skips_the_pair_solver(self):
        image = owner_body(1.)
        result = resolve_world_decision_minus_one(
            image, (0., 0., 0.), 0., 0x19, OWNER, TEMPORARY, .8, .7)

        self.assertFalse(result.collided)
        self.assertEqual(result.impulse_samples, 0)
        self.assertEqual(result.body_image, bytes(image))


if __name__ == '__main__':
    unittest.main()
