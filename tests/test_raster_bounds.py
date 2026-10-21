import unittest

from client.raster_bounds import (RASTER_HEIGHT, RASTER_WIDTH,
                                  occupied_raster_bounds)


class RasterBoundsTests(unittest.TestCase):
    def test_empty_mask_preserves_original_sentinels(self):
        self.assertEqual(occupied_raster_bounds(bytes(RASTER_WIDTH*RASTER_HEIGHT)),
                         (1_000_000, 1_000_000, -1_000_000, -1_000_000, 0))

    def test_counts_nonzero_bytes_and_includes_all_edges(self):
        image = bytearray(RASTER_WIDTH*RASTER_HEIGHT)
        for index, value in ((0, 1), (320, 255), (240*321, 2), (len(image)-1, 3)):
            image[index] = value
        self.assertEqual(occupied_raster_bounds(image), (0, 0, 320, 240, 4))

    def test_single_pixel_bounds(self):
        image = bytearray(RASTER_WIDTH*RASTER_HEIGHT)
        image[103*RASTER_WIDTH+227] = 1
        self.assertEqual(occupied_raster_bounds(image), (227, 103, 227, 103, 1))

    def test_rejects_wrong_dimensions(self):
        with self.assertRaises(ValueError):
            occupied_raster_bounds(bytes(RASTER_WIDTH*RASTER_HEIGHT-1))


if __name__ == '__main__':
    unittest.main()
