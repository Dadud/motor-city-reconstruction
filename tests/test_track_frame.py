import struct
import unittest

from client.track_frame import track_frame


class TrackFrameTests(unittest.TestCase):
    def test_track_table_frame_branch_preserves_source_word_order(self):
        query = bytearray(0x44)
        struct.pack_into('<I', query, 0, 0)
        row = tuple(float(i) for i in range(21))
        point, frame = track_frame(query, (row,))
        self.assertEqual(point, (0.0, 1.0, 2.0))
        self.assertEqual(frame, (9.0, 10.0, 11.0, 3.0, 4.0, 5.0,
                                 6.0, 7.0, 8.0))

    def test_alternate_frame_is_cross_product_then_two_query_vectors(self):
        query = bytearray(0x44)
        struct.pack_into('<I', query, 12, 1)
        struct.pack_into('<6f', query, 44, 1,0,0, 0,1,0)
        point, frame = track_frame(query, (), (7.0, 8.0, 9.0))
        self.assertEqual(point, (7.0, 8.0, 9.0))
        self.assertEqual(frame, (0.0, 0.0, 1.0, 1.0, 0.0, 0.0,
                                 0.0, 1.0, 0.0))


if __name__ == '__main__':
    unittest.main()
