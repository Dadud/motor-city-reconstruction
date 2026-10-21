import struct
import unittest

from client.collision_impulse import CollisionInertia
from client.collision_pair_response import (CollisionImpactBody, resolve_pair_impulse,
                                            resolve_surface_impulse)


IDENTITY = (1., 0., 0., 0., 1., 0., 0., 0., 1.)


def body(address, position, velocity, *, mode=0, image=None):
    inertia = CollisionInertia(1., (1., 1., 1.), IDENTITY, IDENTITY)
    return CollisionImpactBody(
        address, position, velocity, (0., 0., 0.), (0., 0., 0.), inertia,
        1., mode=mode, contact_record=image or bytes(0x400))


class CollisionPairResponseTests(unittest.TestCase):
    def test_inward_pair_writes_reciprocal_contact_and_changes_velocity(self):
        owner = body(0x1000, (0., 0., 0.), (1., 0., 0.))
        target = body(0x2000, (1., 0., 0.), (0., 0., 0.))

        result = resolve_pair_impulse(owner, target, (.5, 0., 0.),
                                      (-1., 0., 0.), .45, .2)

        self.assertTrue(result.collided)
        self.assertEqual(result.samples, 25)
        self.assertEqual(result.effective_mass, .5)
        self.assertEqual(result.owner.linear_velocity, (.5, 0., 0.))
        self.assertEqual(result.target.linear_velocity, (.5, 0., 0.))
        self.assertEqual(struct.unpack_from('<I', result.owner.contact_record, 0x3c4)[0],
                         target.address)
        self.assertEqual(struct.unpack_from('<I', result.target.contact_record, 0x3c4)[0],
                         owner.address)
        self.assertEqual(struct.unpack_from('<I', result.owner.contact_record, 0x3e4)[0], 2)
        self.assertEqual(struct.unpack_from('<3f', result.owner.contact_record, 0x3cc),
                         (-.5, 0., 0.))
        self.assertEqual(struct.unpack_from('<3f', result.target.contact_record, 0x3cc),
                         (.5, 0., 0.))

    def test_inward_surface_writes_support_contact_and_changes_velocity(self):
        support = body(0x1000, (0., 0., 0.), (1., 0., 0.))
        support = CollisionImpactBody(**{**support.__dict__,
                                         'embedded_contact_pointer': 0x12345678})

        result = resolve_surface_impulse(support, (.5, 0., 0.),
                                         (-1., 0., 0.), .45, .2)

        self.assertTrue(result.collided)
        self.assertEqual(result.samples, 28)
        self.assertAlmostEqual(result.body.linear_velocity[0], 0., places=6)
        self.assertEqual(result.body.linear_velocity[1:], (0., 0.))
        self.assertEqual(struct.unpack_from('<I', result.body.contact_record, 0x3c4)[0], 0)
        self.assertEqual(struct.unpack_from('<I', result.body.contact_record, 0x3e4)[0], 2)
        self.assertEqual(struct.unpack_from('<II', result.body.contact_record, 0x3f4),
                         (2, 0x12345678))
        self.assertEqual(struct.unpack_from('<3f', result.body.contact_record, 0x3cc),
                         (-1., 0., 0.))

    def test_separating_surface_leaves_state_unchanged(self):
        sentinel = bytes([0xa5]) * 0x400
        support = body(0x1000, (0., 0., 0.), (-1., 0., 0.), image=sentinel)

        result = resolve_surface_impulse(support, (.5, 0., 0.),
                                         (-1., 0., 0.), .45, .2)

        self.assertFalse(result.collided)
        self.assertEqual(result.samples, 0)
        self.assertEqual(result.body.linear_velocity, support.linear_velocity)
        self.assertEqual(result.body.contact_record, sentinel)

    def test_separating_pair_leaves_records_and_velocities_unchanged(self):
        sentinel = bytes([0xa5]) * 0x400
        owner = body(0x1000, (0., 0., 0.), (-1., 0., 0.), image=sentinel)
        target = body(0x2000, (1., 0., 0.), (0., 0., 0.), image=sentinel)

        result = resolve_pair_impulse(owner, target, (.5, 0., 0.),
                                      (-1., 0., 0.), .45, .2)

        self.assertFalse(result.collided)
        self.assertEqual(result.samples, 0)
        self.assertEqual(result.owner.linear_velocity, owner.linear_velocity)
        self.assertEqual(result.target.linear_velocity, target.linear_velocity)
        self.assertEqual(result.owner.contact_record, sentinel)
        self.assertEqual(result.target.contact_record, sentinel)


if __name__ == '__main__':
    unittest.main()
