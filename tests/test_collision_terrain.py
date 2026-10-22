import unittest

from client.collision_terrain import (triangle_candidate_gate,
                                      triangle_candidate_height_gate,
                                      sample_triangle_candidate_heights,
                                      terrain_response_normal,
                                      terrain_impact_response,
                                      terrain_shape_triangle_indices,
                                      terrain_shape_triangles,
                                      projected_shape_candidates,
                                      terrain_contact_velocity_gate,
                                      specialized_quad_projection_gate,
                                      specialized_quad_projection_candidate,
                                      specialized_quad_height_gate,
                                      sample_specialized_quad_heights,
                                      terrain_contact_lever_arm)
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

    def test_shape_tables_recover_all_original_topologies(self):
        self.assertEqual(len(terrain_shape_triangle_indices(0)), 12)
        self.assertEqual(terrain_shape_triangle_indices(0),
                         terrain_shape_triangle_indices(2))
        self.assertEqual(len(terrain_shape_triangle_indices(1)), 6)
        self.assertEqual(len(terrain_shape_triangle_indices(3)), 40)
        self.assertEqual(terrain_shape_triangle_indices(3),
                         terrain_shape_triangle_indices(4))
        for shape in range(5):
            for triangle in terrain_shape_triangle_indices(shape):
                self.assertEqual(len(triangle), 3)
                self.assertTrue(all(0 <= index < 22 for index in triangle))

    def test_shape_triangles_expand_in_original_order(self):
        vertices = tuple((float(i), float(-i), float(i * 2)) for i in range(22))
        expanded = terrain_shape_triangles(1, vertices)
        self.assertEqual(expanded[0], (vertices[0], vertices[1], vertices[3]))
        self.assertEqual(expanded[-1], (vertices[12], vertices[0], vertices[3]))
        self.assertEqual(len(expanded), 6)

    def test_projected_candidate_search_keeps_table_order_and_indices(self):
        vertices = [(100., 100., 100.)] * 22
        vertices[0] = (0., 0., 0.)
        vertices[4] = (0., 0., 10.)
        vertices[5] = (10., 0., 0.)
        found = projected_shape_candidates(0, (2., 2.), tuple(vertices))
        self.assertTrue(found)
        self.assertEqual(found[0][0], 0)
        self.assertEqual(found[0][1], (0, 4, 5))
        self.assertEqual(found[0][2], (vertices[0], vertices[4], vertices[5]))

    def test_outside_points_fail_signed_edge_gate(self):
        for point in ((20., 20.), (-1., 2.), (2., -1.), (11., 0.)):
            with self.subTest(point=point):
                self.assertFalse(triangle_candidate_gate(point, self.triangle))

    def test_specialized_quad_projection_uses_two_triangles(self):
        quad = ((0., 0., 0.), (0., 0., 10.),
                (10., 0., 10.), (10., 0., 0.))
        self.assertTrue(specialized_quad_projection_gate((2., 8.), quad))
        self.assertTrue(specialized_quad_projection_gate((8., 2.), quad))
        self.assertFalse(specialized_quad_projection_gate((12., 5.), quad))
        self.assertFalse(specialized_quad_projection_gate((0., 5.), quad))
        self.assertFalse(specialized_quad_projection_gate((5., 5.), quad))

    def test_specialized_quad_projection_rejects_degenerate_input_shape(self):
        with self.assertRaises(ValueError):
            specialized_quad_projection_gate((0., 0.), self.triangle)

    def test_specialized_candidate_transforms_corners_and_forwards_max_extent(self):
        local = ((-1., 0., -1.), (-1., 0., 1.),
                 (1., 0., 1.), (1., 0., -1.))
        identity = (1., 0., 0., 0., 1., 0., 0., 0., 1.)
        result = specialized_quad_projection_candidate(
            (3.5, 7.5), local, identity, (4., 2., 7.), .25, .5)
        self.assertEqual(result.transformed_vertices,
                         ((3., 2., 6.), (3., 2., 8.),
                          (5., 2., 8.), (5., 2., 6.)))
        self.assertEqual(result.forwarded_extent, .5)
        self.assertTrue(result.intersects)

    def test_specialized_quad_height_fallback_and_extent_gate(self):
        corners = ((0., 1., 0.), (0., 1., 1.),
                   (1., 1., 1.), (1., 1., 0.))
        result = specialized_quad_height_gate(
            corners, (0., 0., 0., 0.), (0., 0., 0., 0.), .25)
        self.assertEqual(result.heights, (0., 0., 0., 0.))
        self.assertEqual(result.gaps, (1., 1., 1., 1.))
        self.assertFalse(result.accepted)
        shallow = specialized_quad_height_gate(
            corners, (.9, .9, .9, .9), (0., 0., 0., 0.), .25)
        self.assertTrue(shallow.accepted)
        self.assertEqual(shallow.minimum_gap, .10000002384185791)

    def test_specialized_quad_samples_four_track_planes_before_height_gate(self):
        arena, root, seed = fixture(2, 0, 0, 0, 7, 8, 8, 1)
        world = _world(arena, root)
        corners = ((6., 1., 6.), (6., 1., 10.),
                   (10., 1., 10.), (10., 1., 6.))
        result = sample_specialized_quad_heights(
            world, corners, seed, (0., 1., 0.), (0., 0., 0.), .25)
        self.assertEqual(len(result.query_records), 4)
        self.assertEqual(len(result.normals), 4)
        self.assertEqual(result.candidate.minimum_gap, 1.)
        self.assertFalse(result.candidate.accepted)

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
        self.assertEqual(result.normals, ((0., 1., 0.),) * 3)

    def test_motion_gate_requires_all_three_predicted_contacts(self):
        vertices = ((-1., 0., 0.), (0., 0., 1.), (1., 0., 0.))
        normals = ((0., 1., 0.),) * 3
        identity = (1., 0., 0., 0., 1., 0., 0., 0., 1.)
        settled = terrain_contact_velocity_gate(
            vertices, normals, (0., 0., 0.), (0., 0., 0.), (0., 0., 0.),
            (0., 0., 0.), identity, 0.)
        rising = terrain_contact_velocity_gate(
            vertices, normals, (0., 0., 0.), (0., 4., 0.), (0., 0., 0.),
            (0., 0., 0.), identity, 0.)
        self.assertTrue(settled.candidate_accepted)
        self.assertEqual(settled.accepted_indices, (0, 1, 2))
        self.assertFalse(rising.candidate_accepted)
        self.assertEqual(rising.accepted_indices, ())

    def test_contact_lever_arm_rotates_local_center_before_subtracting(self):
        result = terrain_contact_lever_arm(
            (12., -3., 8.), (1.5, -2., .25),
            (0., 0., 1., 0., 1., 0., -1., 0., 0.), (12., 2., 8.))
        self.assertEqual(result, (.25, 7., -1.5))

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
