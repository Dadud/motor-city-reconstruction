import random
import unittest

from client.collision_heading import heading_angle, heading_byte_for_world_coordinates


class CollisionHeadingTests(unittest.TestCase):
    def test_axis_and_diagonal_results(self):
        self.assertEqual(heading_angle(0, 0), 0x2000)
        self.assertEqual(heading_angle(0, 1), 0)
        self.assertEqual(heading_angle(1, 0), 0x4000)
        self.assertEqual(heading_angle(0, -1), 0x8000)
        self.assertEqual(heading_angle(-1, 0), -0x4000)
        self.assertEqual(heading_angle(1, 1), 0x2000)
        self.assertEqual(heading_angle(-1, 1), -0x2000)
        self.assertEqual(heading_angle(1, -1), 0x6000)
        self.assertEqual(heading_angle(-1, -1), -0x6000)

    def test_octants_are_monotonic_at_table_boundaries(self):
        previous = 0
        for value in range(1, 257):
            angle = heading_angle(value, 256)
            self.assertGreaterEqual(angle, previous)
            previous = angle
        self.assertEqual(previous, 0x2000)

    def test_result_is_deterministic_for_signed_32_bit_inputs(self):
        rng = random.Random(0x6f2cc0)
        for _ in range(1000):
            x = rng.randint(-0x80000000, 0x7fffffff)
            z = rng.randint(-0x80000000, 0x7fffffff)
            result = heading_angle(x, z)
            self.assertIsInstance(result, int)
            self.assertTrue(-0x10000 <= result <= 0x10000)

    def test_world_heading_quantizes_to_the_saved_high_byte(self):
        self.assertEqual(heading_byte_for_world_coordinates(1., 0.), 0x40)
        self.assertEqual(heading_byte_for_world_coordinates(0., -1.), 0x80)
        self.assertEqual(heading_byte_for_world_coordinates(-1., 0.), 0xc0)


if __name__ == '__main__':
    unittest.main()
