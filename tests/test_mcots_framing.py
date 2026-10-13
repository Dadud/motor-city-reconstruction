import unittest
from client.mcots_framing import MCOTSFrame
from client.mcots_login import MCOTSLoginRecord


class MCOTSFramingTests(unittest.TestCase):
    def test_native_login_envelope(self):
        payload = MCOTSLoginRecord(123, 42, b'persona', 11, 22, 33).encode_native_record()
        frame = MCOTSFrame(0x12345678, 0, payload)
        wire = frame.encode()
        self.assertEqual(wire[:11], bytes.fromhex('3000544f4d437856341200'))
        self.assertEqual(len(wire), 50)
        self.assertEqual(MCOTSFrame.decode(wire), frame)

    def test_length_boundaries(self):
        frame = MCOTSFrame(0, 255, b'x'*65526)
        self.assertEqual(frame.encode()[:2], b'\xff\xff')
        self.assertEqual(MCOTSFrame.decode(frame.encode()), frame)
        for payload in (b'', b'x'*65527, 'x'):
            with self.assertRaises(ValueError):
                MCOTSFrame(0, 0, payload).encode()

    def test_malformed_envelope(self):
        wire = MCOTSFrame(7, 0, b'x').encode()
        for invalid in (wire[:-1], wire+b'x', wire[:2]+b'FAIL'+wire[6:], wire[:10]):
            with self.assertRaises(ValueError):
                MCOTSFrame.decode(invalid)
        for transaction, flags in ((True, 0), (-1, 0), (2**32, 0), (0, True), (0, 256)):
            with self.assertRaises(ValueError):
                MCOTSFrame(transaction, flags, b'x').encode()
