import struct
import unittest

from client.room_join_request import RoomJoinInputs, build_room_join_argument
from client.room_selection import initialize_room_settings, select_room


def room():
    image = bytearray(b'\xa5' * 0x3c0)
    image[0xa0:0xc0] = b'old\0' + bytes(28)
    struct.pack_into('<H', image, 0xec, 0)
    struct.pack_into('<I', image, 0x3a8, 0)
    struct.pack_into('<I', image, 0x39c, 7)
    return bytes(image)


class RoomSelectionTests(unittest.TestCase):
    def test_initializer_preserves_padding(self):
        image = initialize_room_settings(b'\xa5' * 0x160)
        for start, end in ((0x45, 0x46), (0x4e, 0x50), (0x15a, 0x160)):
            self.assertEqual(image[start:end], b'\xa5' * (end - start))
        self.assertEqual(struct.unpack_from('<I', image, 0x2c)[0], 0x21)

    def test_defaults_feed_join_without_changing_selector(self):
        selection = select_room(room(), b'new')
        inputs = RoomJoinInputs.from_room_image(selection.room_image)
        self.assertEqual((selection.result, selection.source), (1, 'defaults'))
        self.assertEqual((inputs.name, inputs.server_selector, inputs.protocol, inputs.channel_id),
                         (b'new', 7, 0x21, 0))
        self.assertEqual(inputs.opaque_data, bytes(256))
        self.assertEqual(len(build_room_join_argument(inputs)), 0x15c)

    def test_cache_preserves_ready_but_clears_connected(self):
        settings = bytearray(initialize_room_settings(bytes(0x15a)))
        settings[:7] = b'cached\0'
        settings[0x54:0x154] = bytes(range(256))
        struct.pack_into('<II', settings, 0x20, 123, 456)
        struct.pack_into('<H', settings, 0x46, 99)
        struct.pack_into('<H', settings, 0x4c, 1)
        source = bytes(settings)
        selected = select_room(room(), b'cached', cached_settings=source)
        inputs = RoomJoinInputs.from_room_image(selected.room_image)
        self.assertEqual((inputs.channel_id, inputs.max_ready, inputs.opaque_data), (123, 99, bytes(range(256))))
        self.assertEqual(struct.unpack_from('<H', selected.room_image, 0xec)[0], 0)
        self.assertEqual(bytes(settings), source)

    def test_active_connected_or_pending_only_reuses_exact_name(self):
        for offset, fmt in ((0xec, '<H'), (0x3a8, '<I')):
            image = bytearray(room())
            struct.pack_into(fmt, image, offset, 1)
            for name, result in ((b'old', 1), (b'OLD', 0), (b'new', 0)):
                selected = select_room(bytes(image), name, cached_settings=b'invalid unused cache')
                self.assertEqual((selected.result, selected.room_image, selected.source), (result, bytes(image), 'active'))

    def test_invalid_inputs_rejected_before_mutation(self):
        image = room()
        for name in (b'x' * 32, b'a\0b', 'new'):
            with self.assertRaises(ValueError):
                select_room(image, name)
        with self.assertRaises(ValueError):
            select_room(image, b'new', cached_settings=b'bad')


if __name__ == '__main__':
    unittest.main()
