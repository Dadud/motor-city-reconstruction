import struct
import unittest
from client.mcots_data_response import MCOTSDataReply
from client.mcots_framing import MCOTSFrame


class DataReplyTests(unittest.TestCase):
    def test_unaligned_records_continuations_and_extensions(self):
        for request, reply, stride in ((0x144,0x145,569), (0x142,0x143,8), (0x16b,0x16c,516)):
            records = tuple(bytes((index+i*31) & 255 for index in range(stride)) for i in range(3))
            payload = struct.pack('<HHB', reply, 3, 255)+b''.join(records)+b'tail'
            decoded = MCOTSDataReply.from_frame(MCOTSFrame(7,0,payload),
                transaction_value=7, request_operation=request)
            self.assertEqual(decoded.records, records)
            self.assertTrue(decoded.more)
            self.assertEqual(decoded.continuation_value, 255)
            self.assertEqual(decoded.extension, b'tail')
            self.assertNotIn('tail', repr(decoded))

    def test_empty_final_page_and_fixed_reply_preserve_opcode(self):
        decoded = MCOTSDataReply.from_frame(MCOTSFrame(7,0,struct.pack('<HHB',0x143,0,0)),
            transaction_value=7, request_operation=0x142)
        self.assertEqual(decoded.records, ())
        self.assertFalse(decoded.more)
        payload = struct.pack('<H',0x186)+bytes(range(116))
        decoded = MCOTSDataReply.from_frame(MCOTSFrame(7,0,payload+b'extra'),
            transaction_value=7, request_operation=0x185)
        self.assertEqual(decoded.records, (payload,))
        self.assertIsNone(decoded.continuation_value)
        self.assertEqual(decoded.extension, b'extra')

    def test_wrong_identity_and_unbounded_counts_fail(self):
        valid = struct.pack('<HHB',0x143,1,0)+b'12345678'
        for payload, tx, request in ((valid,8,0x142), (valid,7,0x144),
                (valid,7,0x198), (valid[:4],7,0x142), (valid[:-1],7,0x142),
                (struct.pack('<HHB',0x143,65535,0),7,0x142),
                (struct.pack('<H',0x186)+bytes(115),7,0x185)):
            with self.assertRaises(ValueError):
                MCOTSDataReply.from_frame(MCOTSFrame(tx,0,payload),
                    transaction_value=7, request_operation=request)
