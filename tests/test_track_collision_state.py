import struct
import unittest

from client.track_collision_state import (reset_secondary_collision_table,
    reset_track_collision_state)


class TrackCollisionStateTests(unittest.TestCase):
    def test_secondary_helper_preserves_each_row_padding(self):
        image = bytearray([0xA7] * 0x1800)
        reset_secondary_collision_table(image)
        self.assertEqual(struct.unpack_from('<III', image, 0), (0, 0xffffffff, 0))
        self.assertEqual(image[12:24], bytes([0xA7]) * 12)
        self.assertEqual(struct.unpack_from('<III', image, 24), (0, 0xffffffff, 0))

    def test_clears_metadata_block_arrays_and_secondary_rows(self):
        metadata = bytearray([0xA5] * 0xC00)
        blocks = bytearray(2 * 0x6C4)
        first, second = bytearray([0x5A] * 50), bytearray([0x7B] * 26)
        struct.pack_into('<iI', blocks, 0x69C, 2, 0x1000)
        struct.pack_into('<iI', blocks, 0x6C4 + 0x69C, 1, 0x2000)
        secondary = bytearray([0xCC] * 0x1800)
        reset_track_collision_state(metadata, blocks, 1,
            {0x1000: first, 0x2000: second}, secondary)
        self.assertEqual(metadata[:6], b'\xff\0\0\xff\0\0')
        self.assertEqual(struct.unpack_from('<H', first, 2)[0], 0)
        self.assertEqual(struct.unpack_from('<H', first, 26)[0], 0)
        self.assertEqual(first[4:26], bytes([0x5A]) * 22)
        self.assertEqual(struct.unpack_from('<H', second, 2)[0], 0)
        self.assertEqual(struct.unpack_from('<III', secondary),
                         (0, 0xffffffff, 0))

    def test_negative_block_bound_skips_block_table(self):
        metadata = bytearray(0xC00)
        secondary = bytearray(0x1800)
        reset_track_collision_state(metadata, bytearray(), -1, {}, secondary)
        self.assertEqual(metadata[:3], b'\xff\0\0')


if __name__ == '__main__':
    unittest.main()
