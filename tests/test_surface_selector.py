import struct
import unittest

from client.surface_selector import select_surface


class SurfaceSelectorTests(unittest.TestCase):
    def test_positive_and_negative_track_sides_use_separate_bytes(self):
        query = bytes(0x44)
        row = bytearray(0x54)
        struct.pack_into('<3f', row, 0, 0, 0, 0)
        struct.pack_into('<3f', row, 36, 0, 1, 0)
        row[0x50:0x52] = bytes((2, 1))
        self.assertFalse(select_surface((0, 1, 0), 0, query, (row,)))
        self.assertTrue(select_surface((0, -1, 0), 0, query, (row,)))

    def test_descriptor_flag_short_circuits_track_side(self):
        query = bytearray(0x44)
        struct.pack_into('<I', query, 12, 0x1234)
        self.assertTrue(select_surface((0, 0, 0), 0, query, (), 0x20))


if __name__ == '__main__':
    unittest.main()
