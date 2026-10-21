import unittest

from client.matrix_math import (dot_3_f32, integrate_rotation_matrix,
                                repair_rotation_matrix, transpose_3x3_words)


class MatrixMathTests(unittest.TestCase):
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
