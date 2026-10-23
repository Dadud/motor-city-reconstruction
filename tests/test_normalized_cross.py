import math
import unittest

from client.matrix_math import normalized_cross3


class NormalizedCrossTests(unittest.TestCase):
    def test_returns_right_handed_normalized_cross_product(self):
        self.assertEqual(normalized_cross3((1, 0, 0), (0, 1, 0)),
                         (0.0, 0.0, 1.0))

    def test_rounds_each_native_float_output_to_binary32(self):
        self.assertEqual(normalized_cross3((1, 2, 3), (-4, 5, -6)),
                         (-0.8834669589996338, -0.19632600247859955,
                          0.42537298798561096))

    def test_zero_cross_matches_native_nan_result(self):
        result = normalized_cross3((1, 0, 0), (2, 0, 0))
        self.assertTrue(all(math.isnan(value) for value in result))


if __name__ == '__main__':
    unittest.main()
