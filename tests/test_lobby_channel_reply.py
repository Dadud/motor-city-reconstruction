import struct
import unittest

from client.lobby_channel_codec import (
    ChannelJoinRejection, ChannelJoinSuccess, ChannelReplyMailbox)
from client.nps_framing import Frame


class ChannelReplyTests(unittest.TestCase):
    def test_rejection_preserves_status_and_original_conversion(self):
        for raw, result in ((0, 0), (1, 1), (0x7fffffff, 0x7fffffff),
                            (0x80000000, -2147483648), (0xfffffffe, -2),
                            (0xffffffff, -23)):
            reply = ChannelJoinRejection.from_frame(Frame(0x213, struct.pack('>I', raw)))
            self.assertEqual(reply.status, raw)
            self.assertEqual(reply.native_result, result)

    def test_rejection_bounds(self):
        for frame in (Frame(0x214, bytes(4)), Frame(0x213, bytes(3)),
                      Frame(0x213, bytes(5)), Frame(0x213, bytearray(4))):
            with self.assertRaises(ValueError):
                ChannelJoinRejection.from_frame(frame)

    def test_unsolicited_duplicate_and_later_request(self):
        for opcode in (0x213, 0x214, 0x215):
            frame = Frame(opcode, struct.pack('>I', 9) if opcode == 0x213
                          else struct.pack('>II', 4, 8))
            mailbox = ChannelReplyMailbox()
            self.assertFalse(mailbox.receive(frame))
            mailbox.begin()
            self.assertTrue(mailbox.receive(frame))
            first = mailbox.reply
            self.assertFalse(mailbox.receive(frame))
            self.assertIs(mailbox.reply, first)
            self.assertIs(mailbox.take(), first)
            self.assertFalse(mailbox.receive(frame))
            mailbox.begin()
            self.assertIsNone(mailbox.reply)
            self.assertFalse(mailbox.completed)
            self.assertTrue(mailbox.receive(frame))

    def test_malformed_reply_does_not_complete_slot(self):
        mailbox = ChannelReplyMailbox()
        mailbox.begin()
        self.assertFalse(mailbox.receive(Frame(0x217, b'')))
        with self.assertRaises(ValueError):
            mailbox.receive(Frame(0x214, b''))
        self.assertFalse(mailbox.completed)
        self.assertIsNone(mailbox.reply)
        self.assertTrue(mailbox.receive(Frame(0x215, struct.pack('>II', 4, 8))))
        self.assertIsInstance(mailbox.take(), ChannelJoinSuccess)

    def test_single_pending_slot(self):
        mailbox = ChannelReplyMailbox()
        with self.assertRaises(RuntimeError):
            mailbox.take()
        mailbox.begin()
        with self.assertRaises(RuntimeError):
            mailbox.begin()
        with self.assertRaises(RuntimeError):
            mailbox.take()
