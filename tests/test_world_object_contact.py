import struct
import unittest

from client.world_object_contact import prepare_contact_frame


def _row():
    row = [0.0] * 21
    row[0:3] = [10.0, 20.0, 30.0]
    row[3:6] = [0.0, 1.0, 0.0]
    row[6:9] = [0.0, 0.0, 1.0]
    row[9:12] = [1.0, 0.0, 0.0]
    return tuple(row)


class WorldObjectContactTests(unittest.TestCase):
    def test_query_initialization_preserves_tail_and_sets_frame_vectors(self):
        record = bytearray(b'\xa5' * 0x4f8)
        tail = bytes(record[0x390:0x3b4])
        prepare_contact_frame(record, (_row(),), 0, (12, 23, 34), 0)
        self.assertEqual(struct.unpack_from('<8I', record, 0x370), (0, 0, 0, 0, 0, 0, 0, 0))
        self.assertEqual(bytes(record[0x390:0x3b4]), tail)
        self.assertEqual(struct.unpack_from('<9f', record, 0x31c),
                         (1, 0, 0, 0, 1, 0, 0, 0, 1))

    def test_local_position_round_trips_through_track_frame(self):
        record = bytearray(0x4f8)
        prepare_contact_frame(record, (_row(),), 0, (12, 23, 34), 0x4)
        self.assertEqual(struct.unpack_from('<3f', record, 8), (12.0, 23.0, 34.0))
        self.assertEqual(struct.unpack_from('<3f', record, 0x358), (12.0, 23.0, 34.0))
        self.assertEqual(struct.unpack_from('<f', record, 0x3b8)[0], 2.0)

    def test_mode_eight_preserves_owner_position_and_saves_it(self):
        record = bytearray(0x4f8)
        struct.pack_into('<3f', record, 8, -1, -2, -3)
        prepare_contact_frame(record, (_row(),), 0, (12, 23, 34), 0x8)
        self.assertEqual(struct.unpack_from('<3f', record, 8), (-1.0, -2.0, -3.0))
        self.assertEqual(struct.unpack_from('<3f', record, 0x358), (-1.0, -2.0, -3.0))


if __name__ == '__main__':
    unittest.main()
