import struct
import unittest

from client.track_object_indexing import assign_track_object_indices
from client.track_surface_query import (nearest_track_initialization_point,
    nearest_track_quarter_point)


class TrackObjectIndexingTests(unittest.TestCase):
    def test_x87_candidate_ties_can_replace_rounded_initial_distance(self):
        rows = [bytearray(0x54) for _ in range(12)]
        point = (-565.0079345703125, 0., -75.53306579589844)
        self.assertEqual(nearest_track_quarter_point(point, rows), 0)
        self.assertEqual(nearest_track_initialization_point(point, rows), 8)

    def test_assigns_first_nearest_quarter_row_and_clears_delta(self):
        rows = [bytearray(0x54) for _ in range(9)]
        for index, row in enumerate(rows):
            struct.pack_into('<3f', row, 0, float(index * 10), 0., float(index * 10))
        struct.pack_into('<3f', rows[4], 0, 0., 0., 0.)
        record = bytearray([0xA5] * 0x78)
        struct.pack_into('<3f', record, 0, 0., 0., 0.)
        struct.pack_into('<I', record, 0x74, 0)
        struct.pack_into('<3f', record, 0x58, 3., 4., 5.)
        result = assign_track_object_indices((bytes(record),),
            tuple(bytes(row) for row in rows), {})[0]
        self.assertEqual(struct.unpack_from('<ii', result, 0x34), (0, 0))
        self.assertEqual(struct.unpack_from('<3f', result, 0x58), (0., 0., 0.))
        self.assertEqual(result[0x64:], bytes(record)[0x64:])

    def test_animated_objects_use_tick_zero_pose_before_search(self):
        rows = [bytearray(0x54) for _ in range(5)]
        struct.pack_into('<3f', rows[0], 0, 100., 0., 100.)
        struct.pack_into('<3f', rows[4], 0, 0., 0., 0.)
        record = bytearray(0x78)
        struct.pack_into('<3f', record, 0, 100., 0., 100.)
        struct.pack_into('<I', record, 0x74, 0x12340000)
        animation = bytearray(8 + 2 * 20)
        struct.pack_into('<HH', animation, 4, 2, 6)
        struct.pack_into('<3i', animation, 8, 0, 0, 0)
        struct.pack_into('<4h', animation, 20, 0, 0, 0, 16384)
        struct.pack_into('<3i', animation, 28, 10, 20, 30)
        struct.pack_into('<4h', animation, 40, 0, 0, 0, 16384)
        result = assign_track_object_indices((bytes(record),),
            tuple(bytes(row) for row in rows), {0x12340000: bytes(animation)})[0]
        self.assertEqual(struct.unpack_from('<ii', result, 0x34), (4, 0))
        self.assertEqual(struct.unpack_from('<3f', result), (0., 0., 0.))


if __name__ == '__main__':
    unittest.main()
