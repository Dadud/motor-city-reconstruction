import struct
import unittest
from client.mcots_attachment import MCOTSAttachment


class MCOTSAttachmentTests(unittest.TestCase):
    def test_layout_and_name_termination(self):
        for name in (b'', b'persona', b'n'*12, b'n'*13, b'n'*32):
            payload = MCOTSAttachment(123, 42, name).encode()
            self.assertEqual(len(payload), 40)
            self.assertEqual(struct.unpack_from('<HII', payload), (0x1b6, 123, 42))
            self.assertEqual(payload[10:23], bytes(13))
            self.assertEqual(payload[23:36], name[:12].ljust(12, b'\0')+b'\0')
            self.assertEqual(payload[36:], struct.pack('<I', 0x1b5a))

    def test_invalid_identities_and_names(self):
        for value in (-1, 2**32, True):
            with self.assertRaises(ValueError):
                MCOTSAttachment(value, 1, b'persona').encode()
        for name in (b'n'*33, b'a\0b', 'persona'):
            with self.assertRaises(ValueError):
                MCOTSAttachment(1, 2, name).encode()
