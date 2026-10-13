import struct
import unittest
from client.mcots_framing import MCOTSFrame
from client.mcots_response import decode_completion, attachment_status


class MCOTSResponseTests(unittest.TestCase):
    def decode(self, payload, transaction=17):
        return decode_completion(MCOTSFrame(transaction, 0, payload),
                                 transaction_value=17, operation=0x1b6)

    def test_plain_success_and_wrapped_result(self):
        for payload in (b'e\0', struct.pack('<HHI', 0x67, 0x1b6, 0x65)):
            completion = self.decode(payload)
            self.assertTrue(completion.successful)
            self.assertEqual(attachment_status(completion), 1)
        # The generic success dispatcher correlates by envelope transaction;
        # it does not use bytes +2 as an embedded operation.
        self.assertTrue(self.decode(b'e\0arbitrary').successful)

    def test_failure_statuses(self):
        codes = {0x6b: 0x60, 0x7c: 0x5d, 0x82: 7, 0x83: 0x5e,
                 0xba: 0x5f, 0xbb: 0x5a, 0xbc: 0x5c, 0x1b4: 0x5a, 999: 3}
        for opcode in (0x66, 0x107, 0x67):
            for code, status in codes.items():
                completion = self.decode(struct.pack('<HHI', opcode, 0x1b6, code))
                self.assertFalse(completion.successful)
                self.assertEqual(attachment_status(completion), status)
        # 0x65 inside a direct failure record does not turn it into success.
        self.assertFalse(self.decode(struct.pack('<HHI', 0x66, 0x1b6, 0x65)).successful)

    def test_wrong_transaction_and_wrapper_operation(self):
        with self.assertRaises(ValueError):
            self.decode(b'e\0', transaction=18)
        with self.assertRaises(ValueError):
            self.decode(struct.pack('<HHI', 0x67, 0x69, 0x65))

    def test_truncated_or_unhandled_reply(self):
        for payload in (b'x', b'f\0', b'g\0', b'\x07\x01', b'\xd5\0'+bytes(200)):
            with self.assertRaises(ValueError):
                self.decode(payload)
