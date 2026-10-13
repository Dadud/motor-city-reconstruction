import struct
import unittest
from client.mcots_login import MCOTSLoginRecord


class MCOTSLoginTests(unittest.TestCase):
    def test_record_offsets_and_name_boundary(self):
        for name in (b'', b'persona', b'n'*13, b'n'*32):
            record = MCOTSLoginRecord(123, 42, name, 11, 22, 33).encode_native_record()
            self.assertEqual(len(record), 39)
            self.assertEqual(struct.unpack_from('<H5I', record), (0x69, 123, 42, 33, 11, 22))
            self.assertEqual(record[22:35], name[:13].ljust(13, b'\0'))
            self.assertEqual(record[35:], b'Z\x1b\0\0')

    def test_invalid_values_and_name(self):
        for name in (b'a\0b', b'n'*33, 'persona'):
            with self.assertRaises(ValueError):
                MCOTSLoginRecord(1, 2, name, 0, 0, 0).encode_native_record()
        for invalid in (-1, 2**32, True):
            with self.assertRaises(ValueError):
                MCOTSLoginRecord(1, 2, b'name', 0, 0, invalid).encode_native_record()
