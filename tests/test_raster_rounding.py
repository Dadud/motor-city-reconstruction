import math
import unittest

from client.raster_rounding import raster_ceil, raster_floor


class RasterRoundingTests(unittest.TestCase):
    def test_positive_and_negative_fractional_values(self):
        self.assertEqual(raster_ceil(1.25), 2)
        self.assertEqual(raster_ceil(-1.25), -1)
        self.assertEqual(raster_floor(1.25), 1)
        self.assertEqual(raster_floor(-1.25), -2)

    def test_integer_and_signed_zero_values(self):
        for value in (-3.0, -0.0, 0.0, 7.0):
            self.assertEqual(raster_ceil(value), math.ceil(value))
            self.assertEqual(raster_floor(value), math.floor(value))

    def test_int32_float_domain(self):
        self.assertEqual(raster_ceil(-2147483648.0), -2147483648)
        self.assertEqual(raster_floor(2147483520.0), 2147483520)
        for value in (float('inf'), float('-inf'), float('nan'), 2147483648.0):
            with self.subTest(value=value), self.assertRaises(ValueError):
                raster_ceil(value)


if __name__ == '__main__':
    unittest.main()
