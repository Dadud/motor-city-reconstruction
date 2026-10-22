import unittest

from client.collision_edge_contact import (CollisionEdgeRecord,
                                            edge_crossing_mask,
                                            resolve_edge_contact)


class CollisionEdgeContactTests(unittest.TestCase):
    def setUp(self):
        self.polygon = CollisionEdgeRecord(
            0x1000, ((-1., 0., -1.), (1., 1., -1.),
                     (1., 2., 1.), (-1., 3., 1.)), bytes((1, 2, 3, 4)))
        self.other = CollisionEdgeRecord(
            0x2000, ((9., 0., 9.), (10., 0., 9.),
                     (10., 0., 10.), (9., 0., 10.)), bytes(4))

    def test_mask_uses_identity_and_ordered_edge_thresholds(self):
        self.assertEqual(edge_crossing_mask((0., 0., 0.), self.polygon,
                                            self.other), 0)
        self.assertEqual(edge_crossing_mask((2., 0., 0.), self.polygon,
                                            self.other), 0x2)
        self.assertEqual(edge_crossing_mask((2., 0., 0.), self.polygon,
                                            self.polygon), 0)

    def test_edge_contact_returns_normal_point_and_weighted_height(self):
        result = resolve_edge_contact((2., 0., 0.), self.polygon, self.other)
        self.assertTrue(result.accepted)
        self.assertEqual(result.edge_mask, 0x2)
        self.assertEqual(result.normal, (-1., 0., 0.))
        self.assertEqual(result.point, (1., 1., -1.))
        self.assertEqual(result.vertical_value, 2.5)

    def test_no_crossed_edges_returns_zero_outputs(self):
        result = resolve_edge_contact((0., 0., 0.), self.polygon, self.other)
        self.assertFalse(result.accepted)
        self.assertEqual(result.normal, (0., 0., 0.))
        self.assertEqual(result.point, (0., 0., 0.))
        self.assertEqual(result.vertical_value, 0.)

    def test_rejects_malformed_edges_and_nonfinite_query(self):
        with self.assertRaises(ValueError):
            CollisionEdgeRecord(1, ((0., 0., 0.),), b'')
        with self.assertRaises(ValueError):
            edge_crossing_mask((float('nan'), 0., 0.), self.polygon, self.other)


if __name__ == '__main__':
    unittest.main()
