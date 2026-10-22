import unittest

from client.geometry_transform import add_vector_to_points, transform_vertices


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

    def test_transforms_eight_points_for_compact_world_contact_geometry(self):
        points = (1.0, 2.0, 3.0) * 8
        self.assertEqual(transform_vertices(points, (1,0,0,0,1,0,0,0,1),
                                            (10,20,30), count=8),
                         (11.0,22.0,33.0) * 8)

    def test_adds_translation_to_contiguous_points(self):
        self.assertEqual(add_vector_to_points((1, 2, 3, -1, -2, -3),
                                              (.5, 1, 1.5), count=2),
                         (1.5, 3, 4.5, -.5, -1, -1.5))

    def test_translation_accepts_empty_and_rejects_short_or_invalid_input(self):
        self.assertEqual(add_vector_to_points((), (1, 2, 3), count=0), ())
        with self.assertRaises(ValueError):
            add_vector_to_points((0, 1, 2), (1, 2, 3), count=2)
        with self.assertRaises(ValueError):
            add_vector_to_points((0, 1, 2), (1, 2), count=1)


if __name__ == '__main__':
    unittest.main()
