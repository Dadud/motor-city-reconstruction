import unittest

from client.track_vertex_transform import transform_track_vertex


class TrackVertexTransformTests(unittest.TestCase):
    def test_identity_preserves_vertex(self):
        self.assertEqual(transform_track_vertex((1.25, -2.5, 3.75),
                         (1,0,0,0,1,0,0,0,1)), (1.25, -2.5, 3.75))

    def test_uses_column_vectors_from_object_matrix(self):
        matrix=(1,2,3,4,5,6,7,8,9)
        self.assertEqual(transform_track_vertex((2,3,5),matrix),
                         (49.0, 59.0, 69.0))

    def test_rejects_invalid_dimensions(self):
        with self.assertRaises(ValueError):
            transform_track_vertex((1,2), (1,0,0,0,1,0,0,0,1))
        with self.assertRaises(ValueError):
            transform_track_vertex((1,2,3), (1,2,3))


if __name__ == '__main__':
    unittest.main()

