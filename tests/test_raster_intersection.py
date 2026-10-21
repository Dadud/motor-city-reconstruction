import unittest

from client.raster_intersection import raster_scanline_intersections


class RasterIntersectionTests(unittest.TestCase):
    def test_intersects_two_edges_and_orders_left_then_right(self):
        result = raster_scanline_intersections(
            ((1, 0), (5, 10)), ((10, 0), (14, 10)), 5)
        self.assertEqual(result, (3, 12))

    def test_rejects_horizontal_edge_and_nonfinite_input(self):
        with self.assertRaises(ValueError):
            raster_scanline_intersections(
                ((1, 0), (5, 0)), ((10, 0), (14, 10)), 5)
        with self.assertRaises(ValueError):
            raster_scanline_intersections(
                ((1, 0), (5, 10)), ((10, 0), (14, 10)), float('inf'))


if __name__ == '__main__':
    unittest.main()
