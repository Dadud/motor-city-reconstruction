import struct
import unittest

from client.lobby_channel_codec import ChannelJoinRecord, ChannelJoinSuccess, NATIVE_RECORD_SIZE
from client.nps_framing import Frame


class ChannelCodecTests(unittest.TestCase):
    def test_mixed_endian_record_and_counted_nul_strings(self):
        raw = bytearray(NATIVE_RECORD_SIZE)
        struct.pack_into('<I', raw, 0, 0x12345678)
        raw[4:8] = b'abc' + bytes([0])
        struct.pack_into('<I', raw, 0x24, 0x89abcdef)
        struct.pack_into('<H', raw, 0x5c, 0x8001)
        raw[0x88] = 255
        raw[0xa0:0x1a0] = bytes(range(256))
        record = ChannelJoinRecord(bytes(raw))
        wire = record.payload()
        self.assertEqual(wire[:16], bytes.fromhex('12345678000000046162630089abcdef'))
        self.assertEqual(wire[32:34], bytes.fromhex('8001'))
        self.assertEqual(wire[-260:-4], bytes(range(256)))
        self.assertEqual(record.frame().message_id, 0x106)

    def test_strings_and_native_capacity_are_bounded(self):
        for field in ((4, 0x24), (0x74, 0x86)):
            raw = bytearray(NATIVE_RECORD_SIZE)
            raw[field[0]:field[1]] = b'x' * (field[1] - field[0])
            with self.assertRaisesRegex(ValueError, 'NUL'):
                ChannelJoinRecord(bytes(raw)).payload()
        raw = bytearray(NATIVE_RECORD_SIZE)
        raw[4:35] = b'x' * 31
        raw[0x74:0x85] = b'y' * 17
        with self.assertRaisesRegex(ValueError, 'capacity'):
            ChannelJoinRecord(bytes(raw)).payload()
        # Reducing either string by one byte fits the native limit exactly.
        raw[34] = 0
        self.assertEqual(len(ChannelJoinRecord(bytes(raw)).payload()), 0x170)

    def test_success_replies_retain_both_fields(self):
        for message_id in (0x214, 0x215):
            reply = ChannelJoinSuccess.from_frame(Frame(message_id, struct.pack('>II', 123, 0xffffffff)))
            self.assertEqual(reply.channel_id, 123)
            self.assertEqual(reply.value_2, 0xffffffff)
            self.assertEqual(reply.message_id, message_id)
        for frame in (Frame(0x213, bytes(8)), Frame(0x214, bytes(7)), Frame(0x215, bytes(9))):
            with self.assertRaises(ValueError):
                ChannelJoinSuccess.from_frame(frame)
