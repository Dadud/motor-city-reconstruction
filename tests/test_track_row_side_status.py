import struct
import unittest

from client.track_surface_query import (track_row_has_type_two,
    track_row_side_status)


class TrackRowSideStatusTests(unittest.TestCase):
    def setUp(self):
        row = bytearray(0x54)
        struct.pack_into('<3f', row, 0, 1., 2., 3.)
        struct.pack_into('<3f', row, 0x24, 0., 1., 0.)
        row[0x50], row[0x51] = 4, 2
        self.rows = (bytes(row),)

    def test_positive_plane_distance_selects_positive_side_byte(self):
        self.assertEqual(track_row_side_status((1., 3., 3.), self.rows, 0), 2)
        self.assertTrue(track_row_has_type_two((1., 3., 3.), self.rows, 0))

    def test_zero_and_negative_distance_select_other_side(self):
        self.assertEqual(track_row_side_status((1., 2., 3.), self.rows, 0), 4)
        self.assertEqual(track_row_side_status((1., 1., 3.), self.rows, 0), 4)
        self.assertFalse(track_row_has_type_two((1., 2., 3.), self.rows, 0))


if __name__ == '__main__':
    unittest.main()
