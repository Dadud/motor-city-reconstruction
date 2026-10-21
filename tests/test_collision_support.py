import unittest

from client.collision_impulse import CollisionInertia
from client.collision_pair_response import CollisionImpactBody
from client.collision_support import correct_support_geometry, resolve_support_contacts
from tests.test_track_surface_sample import _world
from tools.track_surface_cases import fixture


IDENTITY = (1., 0., 0., 0., 1., 0., 0., 0., 1.)
INERTIA = CollisionInertia(1., (1., 1., 1.), IDENTITY, IDENTITY)


class CollisionSupportGeometryTests(unittest.TestCase):
    def test_positive_local_height_points_skip_surface_lookup(self):
        arena, root, seed = fixture(2, 0, 0, 0, 7, 8, 8, 1)
        points = (0., 2., 0.) * 22

        result = correct_support_geometry(_world(arena, root), (8., 7., 8.),
                                          IDENTITY, points, (seed,) * 22, 0.)

        self.assertEqual(len(result.queries), 22)
        self.assertTrue(all(not query.eligible and query.normal is None
                            for query in result.queries))
        self.assertEqual(result.position, (8., 7., 8.))
        self.assertEqual(result.correction, (0., 0., 0.))

    def test_penetrating_point_corrects_body_and_all_world_support_points(self):
        arena, root, seed = fixture(2, 0, 0, 0, 7, 8, 8, 1)
        points = [0., 2., 0.] * 22
        points[:3] = (0., -.1, 0.)

        result = correct_support_geometry(_world(arena, root), (8., -.8, 8.),
                                          IDENTITY, points, (seed,) * 22, 0.)

        self.assertTrue(result.queries[0].eligible)
        self.assertGreater(result.correction[1], .9)
        self.assertAlmostEqual(result.position[1], .12437, places=4)
        self.assertAlmostEqual(result.world_points[0][1], result.position[1] - .1,
                               places=5)
        self.assertEqual(result.relative_points[0], 0.)
        self.assertAlmostEqual(result.relative_points[1], -.1, places=7)
        self.assertEqual(result.relative_points[2], 0.)

    def test_second_pass_selects_surface_material_and_applies_impulse(self):
        arena, root, seed = fixture(2, 0, 0, 0, 7, 8, 8, 1)
        arena[0x50c4:0x50c6] = (4).to_bytes(2, 'little', signed=True)
        world = _world(arena, root)
        points = [0., 2., 0.] * 22
        points[:3] = (0., -.1, 0.)
        geometry = correct_support_geometry(world, (8., -.8, 8.), IDENTITY,
                                            points, (seed,) * 22, -1.)
        body = CollisionImpactBody(0x1000, (8., -.8, 8.), (0., -1., 0.),
                                   (0., 0., 0.), (0., 0., 0.), INERTIA, 1.,
                                   contact_record=bytes(0x400))
        coefficients = ((.45, .2),) * 32

        result = resolve_support_contacts(world, body, geometry, coefficients,
                                          1., 0)

        self.assertEqual(result.support_count, 1)
        self.assertEqual(result.impacted_points, (0,))
        self.assertEqual(result.body.contact_record[0x3f4], 2)
        self.assertEqual(result.body.contact_record[0x3f8], 4)
        self.assertGreater(result.body.linear_velocity[1], -1.)


if __name__ == '__main__':
    unittest.main()
