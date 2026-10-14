import struct
import unittest
from client.connection_registry import (ConnectionRegistryEntry,
                                        allocate_connection_id, find_existing_connection)


class ConnectionRegistryTests(unittest.TestCase):
    def test_counter_keeps_zero_and_wraps(self):
        self.assertEqual(allocate_connection_id(0), (0, 1))
        self.assertEqual(allocate_connection_id(0xffffffff), (0xffffffff, 0))
        self.assertEqual(allocate_connection_id(0x7fffffff), (0x7fffffff, 0x80000000))
        for invalid in (-1, 0x100000000, True):
            with self.assertRaises(ValueError):
                allocate_connection_id(invalid)

    def test_lookup_is_exact_first_match_and_uses_c_strings(self):
        entries = [ConnectionRegistryEntry(0, b'Name\0junk', b'Host\0', 80),
                   ConnectionRegistryEntry(7, b'Name\0', b'Host\0', 80)]
        self.assertEqual(find_existing_connection(entries, b'Name\0', b'Host\0tail', 80), 0)
        self.assertEqual(find_existing_connection(entries, b'name\0', b'Host\0', 80), -20)
        self.assertEqual(find_existing_connection(entries, b'Name\0', b'Host\0', 81), -20)
        self.assertEqual(find_existing_connection([], b'\0', b'\0', 0), -20)

    def test_image_and_signed_id(self):
        image = bytearray(0x178)
        struct.pack_into('<I', image, 4, 0xffffffff)
        image[8:10] = b'h\0'
        image[0x10c:0x10e] = b'u\0'
        struct.pack_into('<I', image, 0x174, 65535)
        entry = ConnectionRegistryEntry.from_image(bytes(image))
        self.assertEqual(find_existing_connection([entry], b'u\0', b'h\0', 65535), -1)
        with self.assertRaises(ValueError):
            ConnectionRegistryEntry.from_image(bytes(0x177))
        with self.assertRaises(ValueError):
            ConnectionRegistryEntry(1, b'unterminated', b'h\0', 80)
