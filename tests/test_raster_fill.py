import unittest

from client.raster_fill import rasterize_projected_triangle


class RasterFillTests(unittest.TestCase):
    def test_projects_and_fills_inclusive_triangle_spans(self):
        mask = rasterize_projected_triangle(
            ((1, 1), (9, 1), (5, 9)), (0, 10), (0, 10))
        occupied = [index for index, value in enumerate(mask) if value]
        self.assertEqual(len(occupied), 24769)
        self.assertEqual((min(i % 321 for i in occupied),
                          min(i // 321 for i in occupied),
                          max(i % 321 for i in occupied),
                          max(i // 321 for i in occupied)), (32, 24, 288, 216))

    def test_degenerate_after_clipping_is_empty(self):
        mask = rasterize_projected_triangle(
            ((-1, 5), (5, 5), (11, 5)), (0, 10), (0, 10))
        self.assertFalse(any(mask))


if __name__ == '__main__':
    unittest.main()
