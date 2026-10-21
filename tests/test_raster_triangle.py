import unittest

from client.raster_triangle import order_triangle_vertices_by_y


class RasterTriangleTests(unittest.TestCase):
    def test_orders_distinct_y_from_low_to_high(self):
        result = order_triangle_vertices_by_y(((1, 10), (2, 30), (3, 20)))
        self.assertEqual(result, ((1, 10), (3, 20), (2, 30)))

    def test_matches_original_tie_order_for_horizontal_triangle(self):
        result = order_triangle_vertices_by_y(((1, 10), (2, 10), (3, 10)))
        self.assertEqual(result, ((1, 10), (3, 10), (2, 10)))

    def test_rejects_wrong_shape_and_nonfinite_coordinates(self):
        with self.assertRaises(ValueError):
            order_triangle_vertices_by_y(((1, 0), (2, 1)))
        with self.assertRaises(ValueError):
            order_triangle_vertices_by_y(((1, 0), (2, 1), (3, float('nan'))))


if __name__ == '__main__':
    unittest.main()
