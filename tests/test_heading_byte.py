import unittest

from client.heading_byte import heading_byte


class HeadingByteTests(unittest.TestCase):
    def test_axes_octants_and_diagonal(self):
        cases = {
            (0, 0): 0x80,
            (1, 0): 0x100,
            (0, 1): 0,
            (0, -1): 0x200,
            (-1, 0): -0x100,
            (1, 1): 0x80,
            (-1, 1): -0x80,
            (1, -1): 0x180,
            (-1, -1): -0x180,
        }
        for coordinates, expected in cases.items():
            with self.subTest(coordinates=coordinates):
                self.assertEqual(heading_byte(*coordinates), expected)

    def test_supported_int32_domain(self):
        self.assertGreaterEqual(heading_byte(-0x7fffffff, 0x7fffffff), -0x200)
        self.assertLessEqual(heading_byte(0x7fffffff, -0x7fffffff), 0x300)
        for coordinates in ((-0x80000000, 0), (0, -0x80000000),
                            (0x80000000, 0), (0., 1)):
            with self.subTest(coordinates=coordinates), self.assertRaises(ValueError):
                heading_byte(*coordinates)


if __name__ == '__main__':
    unittest.main()
