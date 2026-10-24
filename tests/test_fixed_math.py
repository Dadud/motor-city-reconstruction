import unittest

from client.fixed_math import signed_ratio_16_16


class FixedMathTests(unittest.TestCase):
    def test_signed_16_16_ratio(self):
        self.assertEqual(signed_ratio_16_16(1, 2), 0x8000)
        self.assertEqual(signed_ratio_16_16(-1, 2), -0x8000)
        self.assertEqual(signed_ratio_16_16(7, 2), 3 * 0x10000 + 0x8000)
        self.assertEqual(signed_ratio_16_16(-7, 2), -(3 * 0x10000 + 0x8000))
        self.assertEqual(signed_ratio_16_16(7, -2), -(3 * 0x10000 + 0x8000))
        self.assertEqual(signed_ratio_16_16(-7, -2), 3 * 0x10000 + 0x8000)

    def test_result_wraps_like_int32(self):
        self.assertEqual(signed_ratio_16_16(0x7fffffff, 1), -0x10000)
        self.assertEqual(signed_ratio_16_16(-0x80000000, 1), 0)

    def test_rejects_divide_fault_and_invalid_width(self):
        for numerator, denominator in ((1, 0), (-0x80000000, -1), (1 << 31, 1)):
            with self.subTest(numerator=numerator, denominator=denominator):
                with self.assertRaises(ValueError):
                    signed_ratio_16_16(numerator, denominator)


if __name__ == '__main__':
    unittest.main()
