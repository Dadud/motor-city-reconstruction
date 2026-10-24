import struct
import unittest

from client.animated_track_objects import update_animated_track_objects


class AnimatedTrackObjectTests(unittest.TestCase):
    def test_updates_only_animated_records_and_scaled_position_deltas(self):
        first = bytearray([0xA5] * 0x78)
        struct.pack_into('<3f', first, 0, 1., -2., 3.5)
        struct.pack_into('<I', first, 0x74, 0x12345678)
        second_image = bytearray([0x5A] * 0x78)
        struct.pack_into('<I', second_image, 0x74, 0)
        second = bytes(second_image)
        result = update_animated_track_objects(
            (bytes(first), second), .5,
            lambda index, record: (4., 2., -1.))
        self.assertEqual(struct.unpack_from('<3f', result[0]), (4., 2., -1.))
        self.assertEqual(struct.unpack_from('<3f', result[0], 0x58),
                         (1.5, 2., -2.25))
        self.assertEqual(result[0][12:0x58], bytes(first)[12:0x58])
        self.assertEqual(result[0][0x64:], bytes(first)[0x64:])
        self.assertEqual(result[1], second)


if __name__ == '__main__':
    unittest.main()
