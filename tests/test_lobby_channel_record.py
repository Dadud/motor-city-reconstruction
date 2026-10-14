import struct
import unittest

from client.lobby_channel_record import (CHANNEL_ALLOCATION_SIZE, CHANNEL_ARGUMENT_SIZE,
                                        initialize_channel_image, materialize_channel_record)


class ChannelRecordTests(unittest.TestCase):
    def argument(self, flags=0, name=b'room'):
        argument = bytearray(CHANNEL_ARGUMENT_SIZE)
        argument[0x10:0x10 + len(name)] = name
        struct.pack_into('<I', argument, 0xc, flags)
        return bytes(argument)

    def test_unwritten_allocation_bytes_remain_explicit(self):
        initial = bytes([0xab]) * CHANNEL_ALLOCATION_SIZE
        image = initialize_channel_image(self.argument(), initial)
        self.assertEqual(image[0x2a:0x2c], b'\xab\xab')
        self.assertEqual(image[0x81], 0xab)
        record = materialize_channel_record(image)
        self.assertEqual(record.native[0x22:0x24], b'\xab\xab')
        self.assertEqual(record.native[0x85], 0xab)
        self.assertEqual(record.native[0x8a:0x8c], b'\xab\xab')
        self.assertEqual(record.native[0x58:0x5c], bytes(4))

    def test_flag_precedence_and_opaque_full_flags(self):
        for flags, mode in ((0, 2), (1, 1), (4, 4), (5, 1), (0x4025, 1)):
            with self.subTest(flags=flags):
                image = initialize_channel_image(self.argument(flags), bytes(CHANNEL_ALLOCATION_SIZE))
                record = materialize_channel_record(image).native
                self.assertEqual(struct.unpack_from('<H', record, 0x66)[0], mode)
                self.assertEqual(struct.unpack_from('<H', record, 0x62)[0], flags & 0x20)
                self.assertEqual(struct.unpack_from('<H', record, 0x86)[0], flags & 0x4000)
                self.assertEqual(struct.unpack_from('<I', record, 0x1a0)[0], flags)

    def test_names_follow_bounded_strncpy_including_padding(self):
        initial = bytes([0xcc]) * CHANNEL_ALLOCATION_SIZE
        for name in (b'', b'a\0tail', b'x' * 30):
            image = initialize_channel_image(self.argument(name=name), initial)
            self.assertEqual(image[0xc:0x2a], name.split(b'\0', 1)[0].ljust(30, b'\0'))
            self.assertEqual(image[0x2a:0x2c], b'\xcc\xcc')
        # A 30-byte nonterminated name plus nonzero heap tail cannot be framed.
        image = initialize_channel_image(self.argument(name=b'x' * 30), initial)
        with self.assertRaises(ValueError):
            materialize_channel_record(image).payload()

    def test_complete_raw_mapping_uses_explicit_caller_connection_overrides(self):
        image = bytearray(initialize_channel_image(self.argument(), bytes(CHANNEL_ALLOCATION_SIZE)))
        struct.pack_into('<II', image, 0x2c, 0xffffffff, 1)
        struct.pack_into('<III', image, 0x58, 7003, 0x42, 123)
        record = materialize_channel_record(bytes(image)).native
        self.assertEqual(struct.unpack_from('<II', record, 0x24), (0xffffffff, 1))
        self.assertEqual(struct.unpack_from('<III', record, 0x50), (7003, 0x42, 123))

    def test_wrong_sizes_and_mutable_inputs_are_rejected(self):
        for argument in (b'', bytes(CHANNEL_ARGUMENT_SIZE - 1), bytearray(CHANNEL_ARGUMENT_SIZE)):
            with self.assertRaises(ValueError):
                initialize_channel_image(argument, bytes(CHANNEL_ALLOCATION_SIZE))
        with self.assertRaises(ValueError):
            initialize_channel_image(self.argument(), bytes(CHANNEL_ALLOCATION_SIZE - 1))
        with self.assertRaises(ValueError):
            materialize_channel_record(bytes(CHANNEL_ALLOCATION_SIZE + 1))
