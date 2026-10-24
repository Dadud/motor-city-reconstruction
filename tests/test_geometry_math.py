import unittest

from client.geometry_math import rounded_oriented_area2


class GeometryMathTests(unittest.TestCase):
    def test_oriented_area_sign_and_rounding(self):
        self.assertEqual(rounded_oriented_area2((0., 0.), (2., 0.), (0., 3.)), 6)
        self.assertEqual(rounded_oriented_area2((0., 0.), (0., 3.), (2., 0.)), -6)
        self.assertEqual(rounded_oriented_area2((0., 0.), (1., 0.), (0., 0.5)), 0)
        self.assertEqual(rounded_oriented_area2((0., 0.), (1., 0.), (0., 1.5)), 2)

    def test_oriented_area_requires_finite_2d_points(self):
        for points in (((0.,), (1., 0.), (0., 1.)),
                       ((0., 0.), (1., float('inf')), (0., 1.))):
            with self.subTest(points=points), self.assertRaises(ValueError):
                rounded_oriented_area2(*points)


if __name__ == '__main__':
    unittest.main()
