import struct
import unittest

from client.track_block_membership import contains_track_block_id


class TrackBlockMembershipTests(unittest.TestCase):
    def test_scans_signed_ids_from_selected_row_inclusive(self):
        table = bytearray(3 * 0x6C4 + 0x190 + 3 * 4)
        struct.pack_into('<h', table, 3 * 0x6C4 + 0x190, -8)
        struct.pack_into('<h', table, 3 * 0x6C4 + 0x190 + 2 * 4, 17)
        self.assertTrue(contains_track_block_id(table, 2, 17, 3))
        self.assertFalse(contains_track_block_id(table, 1, 17, 3))

    def test_shortcut_and_negative_global_count(self):
        self.assertTrue(contains_track_block_id(b'', -1, 4, 4))
        self.assertFalse(contains_track_block_id(b'', -1, 5, 4))

    def test_rejects_incomplete_memory_view(self):
        with self.assertRaises(ValueError):
            contains_track_block_id(bytes(8), 1, 9, 0)


if __name__ == '__main__':
    unittest.main()
