import unittest

from client.geometry_transform import transform_vertices


class GeometryTransformTests(unittest.TestCase):
    def test_transforms_all_22_vertices_with_client_matrix_layout(self):
        local = (1.0, 2.0, 3.0) * 22
        matrix = (1, 2, 3, 4, 5, 6, 7, 8, 9)
        output = transform_vertices(local, matrix, (10, 20, 30))
        self.assertEqual(output, (40.0, 56.0, 72.0) * 22)

    def test_rejects_wrong_vertex_count_or_short_buffer(self):
        with self.assertRaises(ValueError):
            transform_vertices((0.0,) * 66, (1,0,0,0,1,0,0,0,1), (0,0,0), count=12)
        with self.assertRaises(ValueError):
            transform_vertices((0.0,) * 3, (1,0,0,0,1,0,0,0,1), (0,0,0))


if __name__ == '__main__':
    unittest.main()
