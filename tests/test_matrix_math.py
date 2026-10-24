import unittest

from client.matrix_math import (atan2_turns, cross_product3, dot_3_f32, dot_product_batch, integrate_rotation_matrix,
                                normalize_vector3, repair_rotation_matrix,
                                transpose_3x3_words)


class MatrixMathTests(unittest.TestCase):
    def test_x87_atan2_returns_turns_with_native_constant(self):
        self.assertEqual(atan2_turns(1, 0), 1.5707963267948966*0.15915493667125702)
        self.assertEqual(atan2_turns(0, 1), 0.0)
        self.assertAlmostEqual(atan2_turns(-1, -1), -0.375, places=7)

    def test_transposes_nine_words(self):
        self.assertEqual(transpose_3x3_words(range(9)), (0, 3, 6, 1, 4, 7, 2, 5, 8))

    def test_preserves_float_bit_patterns_without_interpreting_them(self):
        words = (0x7fc12345, 0x80000000, 0x00000000,
                 0x3f800000, 0xbf800000, 0x7f800000,
                 0xff800000, 0x00000001, 0xffffffff)
        self.assertEqual(transpose_3x3_words(words),
                         (words[0], words[3], words[6], words[1], words[4], words[7],
                          words[2], words[5], words[8]))

    def test_rejects_wrong_shape_and_width(self):
        for words in ((1, 2), (0,) * 8, (0,) * 10, (0,)*8 + (-1,), (0,)*8 + (1 << 32,)):
            with self.subTest(words=words), self.assertRaises(ValueError):
                transpose_3x3_words(words)

    def test_three_component_dot_product(self):
        self.assertEqual(dot_3_f32((1, 2, 3), (4, -5, 6)), 12.0)
        self.assertEqual(dot_3_f32((1e20, 1, -1e20), (1, 1, 1)), 0.0)
        with self.assertRaises(ValueError):
            dot_3_f32((1, 2), (3, 4))

    def test_dot_product_batch(self):
        self.assertEqual(dot_product_batch(((1, 2, 3), (-1, 0, 1)), (4, -5, 6)),
                         (12.0, 2.0))
        self.assertEqual(dot_product_batch((), (1, 2, 3)), ())
        with self.assertRaises(ValueError):
            dot_product_batch(((1, 2),), (1, 2, 3))

    def test_normalize_three_component_vector(self):
        self.assertEqual(normalize_vector3((3, 0, 4)), (0.6000000238418579, 0.0, 0.800000011920929))
        self.assertTrue(all(value != value for value in normalize_vector3((0, 0, 0))))
        with self.assertRaises(ValueError):
            normalize_vector3((1, 2))

    def test_cross_product_three_component_vectors(self):
        self.assertEqual(cross_product3((1, 0, 0), (0, 1, 0)), (0.0, 0.0, 1.0))
        self.assertEqual(cross_product3((1, 2, 3), (-4, 5, -6)), (-27.0, -6.0, 13.0))
        with self.assertRaises(ValueError):
            cross_product3((1, 2), (3, 4, 5))

    def test_rotation_matrix_increment_uses_turns_and_x_y_z_order(self):
        identity=(1,0,0,0,1,0,0,0,1)
        self.assertEqual(integrate_rotation_matrix(identity,(0,0,0)), identity)
        result=integrate_rotation_matrix(identity,(0.25,0,0))
        self.assertAlmostEqual(result[4],0.0,places=6)
        self.assertAlmostEqual(result[5],1.0,places=6)

    def test_rotation_matrix_repair_preserves_identity_and_corrects_drift(self):
        identity=(1,0,0,0,1,0,0,0,1)
        self.assertEqual(repair_rotation_matrix(identity),identity)
        drifted=(1.01,0.01,0,-0.01,0.99,0.02,0,-0.02,1.02)
        repaired=repair_rotation_matrix(drifted)
        self.assertEqual(len(repaired),9)
        self.assertLess(abs(sum(repaired[i]**2 for i in (0,3,6))-1),1e-5)


if __name__ == '__main__':
    unittest.main()
