import random
import struct
import unittest

from client.room_join_request import RoomJoinInputs
from client.room_settings import apply_room_settings, ROOM_SETTINGS_MIN_SIZE


class RoomSettingsTests(unittest.TestCase):
    def source(self):
        source = bytearray(random.Random(0x44a9d0).randbytes(ROOM_SETTINGS_MIN_SIZE))
        source[:4] = b'new\0'
        source[0x30:0x32] = b'x\0'
        return bytes(source)

    def test_copies_known_fields_and_preserves_all_other_bytes(self):
        room = bytes([0xa5]) * 0x3c0
        source = self.source()
        result = apply_room_settings(room, source)
        expected = bytearray(room)
        ranges = ((0, 4), (0x54, 256), (0x30, 2), (0x20, 16),
                  (0x40, 5), (0x46, 8), (0x50, 4), (0x154, 6))
        for offset, size in ranges:
            expected[0xa0+offset:0xa0+offset+size] = source[offset:offset+size]
        self.assertEqual(result, bytes(expected))
        inputs = RoomJoinInputs.from_room_image(result)
        self.assertEqual(inputs.name, b'new')
        self.assertEqual(inputs.server_selector, 0xa5a5a5a5)
        self.assertEqual(inputs.protocol, struct.unpack_from('<I', source, 0x2c)[0])
        self.assertEqual(inputs.channel_id, struct.unpack_from('<I', source, 0x20)[0])
        self.assertEqual(inputs.max_ready, struct.unpack_from('<H', source, 0x46)[0])
        self.assertEqual(inputs.opaque_data, source[0x54:0x154])

    def test_maximum_strings_copy_their_terminators(self):
        source = bytearray(self.source())
        source[:32] = b'n'*31 + b'\0'
        source[0x30:0x40] = b's'*15 + b'\0'
        result = apply_room_settings(bytes(0x3c0), bytes(source))
        self.assertEqual(result[0xa0:0xc0], source[:32])
        self.assertEqual(result[0xd0:0xe0], source[0x30:0x40])

    def test_rejects_invalid_images_and_unterminated_strings(self):
        source = self.source()
        for room in (bytes(0x1f9), bytes(65537), bytearray(0x3c0)):
            with self.assertRaises(ValueError):
                apply_room_settings(room, source)
        for bad in (source[:-1], bytearray(source), bytes(65537)):
            with self.assertRaises(ValueError):
                apply_room_settings(bytes(0x3c0), bad)
        for offset, size in ((0, 32), (0x30, 16)):
            bad = bytearray(source)
            bad[offset:offset+size] = b'x'*size
            with self.assertRaises(ValueError):
                apply_room_settings(bytes(0x3c0), bytes(bad))
