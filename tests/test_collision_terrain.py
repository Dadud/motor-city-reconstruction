import unittest

from client.collision_terrain import triangle_candidate_gate


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


if __name__ == '__main__':
    unittest.main()
