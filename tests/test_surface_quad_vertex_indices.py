import unittest

from client.track_surface import surface_quad_vertex_indices


class SurfaceQuadVertexIndicesTests(unittest.TestCase):
    def test_resolves_quad_index_through_descriptor(self):
        descriptors = ((0, 0, 0, 1), (0, 0, 0, 0))
        quads = ((9, 8, 7, 6), (1, 3, 5, 7))
        self.assertEqual(surface_quad_vertex_indices(3, 0, descriptors, quads),
                         (1, 3, 5, 7))

    def test_rejects_missing_descriptor(self):
        with self.assertRaises(ValueError):
            surface_quad_vertex_indices(0, 1, ((0, 0, 0, 0),), ((0, 1, 2, 3),))

    def test_rejects_bad_quad_shape(self):
        with self.assertRaises(ValueError):
            surface_quad_vertex_indices(0, 0, ((0, 0, 0, 0),), ((0, 1, 2),))


if __name__ == '__main__':
    unittest.main()
