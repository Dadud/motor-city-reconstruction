import unittest

from client.collision_terrain import (triangle_candidate_gate,
                                      triangle_candidate_height_gate,
                                      sample_triangle_candidate_heights,
                                      terrain_response_normal,
                                      terrain_impact_response)
from tests.test_track_surface_sample import _world
from tools.track_surface_cases import fixture


class TerrainTriangleGateTests(unittest.TestCase):
    def setUp(self):
        # Clockwise in XZ, matching the source's signed edge inequalities.
        self.triangle = ((0., 0., 0.), (0., 0., 10.), (10., 0., 0.))

    def test_inside_and_boundary_points_pass(self):
        self.assertTrue(triangle_candidate_gate((2., 2.), self.triangle))
        self.assertTrue(triangle_candidate_gate((0., 0.), self.triangle))
        self.assertTrue(triangle_candidate_gate((0., 10.), self.triangle))

    def test_outside_points_fail_signed_edge_gate(self):
        for point in ((20., 20.), (-1., 2.), (2., -1.), (11., 0.)):
            with self.subTest(point=point):
                self.assertFalse(triangle_candidate_gate(point, self.triangle))

    def test_degenerate_consecutive_vertices_fail(self):
        degenerate = (self.triangle[0], self.triangle[0], self.triangle[2])
        self.assertFalse(triangle_candidate_gate((1., 1.), degenerate))

    def test_requires_three_xyz_vertices(self):
        with self.assertRaises(ValueError):
            triangle_candidate_gate((1., 1.), self.triangle[:2])

    def test_height_gate_accepts_contact_and_rejects_clearance(self):
        contact = triangle_candidate_height_gate(
            self.triangle, (0., 0., 0.), (0., 0., 0.))
        clearance = triangle_candidate_height_gate(
            ((0., 1., 0.), (0., 1., 10.), (10., 1., 0.)),
            (0., 0., 0.), (0., 0., 0.))
        self.assertTrue(contact.accepted)
        self.assertEqual(contact.minimum_gap, 0.)
        self.assertFalse(clearance.accepted)
        self.assertEqual(clearance.gaps, (1., 1., 1.))

    def test_surface_deviation_uses_object_plane_fallback(self):
        result = triangle_candidate_height_gate(
            ((0., 0.1, 0.), (0., 0.2, 10.), (10., -0.1, 0.)),
            (0.8, -0.4, -0.8), (0., 0., 0.))
        self.assertEqual(result.heights, (0., 0., 0.))
        for actual, expected in zip(result.gaps, (0.1, 0.2, -0.1)):
            self.assertAlmostEqual(actual, expected, places=6)

    def test_height_gate_threshold_is_inclusive(self):
        result = triangle_candidate_height_gate(
            ((0., 0.1016, 0.), (0., 0.2, 10.), (10., 0.3, 0.)),
            (0., 0., 0.), (0., 0., 0.))
        self.assertTrue(result.accepted)
        self.assertAlmostEqual(result.minimum_gap, 0.1016, places=6)

    def test_half_unit_fallback_boundaries_are_inclusive(self):
        result = triangle_candidate_height_gate(
            ((0., 0.5, 0.), (0., -0.5, 10.), (10., 0.4, 0.)),
            (0., 0., 0.), (10., 10., 10.))
        self.assertEqual(result.heights, (0., 0., 0.))
        self.assertTrue(result.accepted)

    def test_candidate_height_sampler_composes_track_lookup_and_plane(self):
        arena, root, seed = fixture(2, 0, 0, 0, 7, 8, 8, 1)
        vertices = ((6., 1., 6.), (6., 1., 10.), (10., 1., 6.))

        result = sample_triangle_candidate_heights(
            _world(arena, root), vertices, seed, (0., 1., 0.), (0., 0., 0.))

        self.assertFalse(result.candidate.accepted)
        self.assertEqual(result.candidate.gaps, (1., 1., 1.))
        self.assertEqual(len(result.query_records), 3)

    def test_response_normal_is_upward_and_degenerate_is_zero(self):
        self.assertEqual(terrain_response_normal(self.triangle), (0., 1., 0.))
        reverse = (self.triangle[0], self.triangle[2], self.triangle[1])
        self.assertEqual(terrain_response_normal(reverse), (0., 1., 0.))
        self.assertEqual(terrain_response_normal((self.triangle[0],) * 3),
                         (0., 0., 0.))

    def test_terrain_impulse_respects_load_and_work_limits(self):
        normal = (0., 1., 0.)
        limited = terrain_impact_response((1., 0., 0.), (0., 0., 0.),
                                          1., normal, .45, .2)
        full = terrain_impact_response((1., 0., 0.), (0., 0., 0.),
                                       1., normal, 4., .5)
        unloaded = terrain_impact_response((1., 0., 0.), (0., 0., 0.),
                                           1., (0., -1., 0.), .45, .2)
        self.assertTrue(limited.applied)
        self.assertEqual(limited.response_status, 2)
        self.assertEqual(full.response_status, 1)
        self.assertFalse(unloaded.applied)
        self.assertEqual(unloaded.linear_velocity, (1., 0., 0.))


if __name__ == '__main__':
    unittest.main()
