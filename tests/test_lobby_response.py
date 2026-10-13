import struct
import unittest

from client.lobby_response import LobbyLoginSuccess, native_connection_rejection
from client.nps_framing import Frame


class LobbyResponseTests(unittest.TestCase):
    def test_connection_rejections_preserve_native_return_codes(self):
        for message_id, code in ((0x21e, -34), (0x22a, -135), (0x20a, -3),
                                 (0x20b, -4), (0x213, -23), (0x22b, -140)):
            self.assertEqual(native_connection_rejection(message_id), code)
        for message_id in (0x120, 0x308, 0x230, 0x231, 0xffff):
            self.assertIsNone(native_connection_rejection(message_id))
        for message_id in (-1, 65536, True, '0x21e'):
            with self.assertRaises(ValueError):
                native_connection_rejection(message_id)

    def test_native_username_forces_terminator_without_altering_wire_bytes(self):
        for wire, native in ((b'n'*32, b'n'*31), (b'a\0b', b'a'),
                             (b'driver\0', b'driver'), (b'', b'')):
            result = LobbyLoginSuccess(42, wire, bytes(64))
            self.assertEqual(result.native_username, native)
            self.assertEqual(result.username, wire)

    def test_success_ids_and_opaque_counted_bytes(self):
        for message_id in (0x120, 0x308):
            for username in (b'', b'driver\0', b'a\0b', b'n'*32):
                blob = bytes(range(64))
                result = LobbyLoginSuccess.from_frame(Frame(message_id,
                    struct.pack('>II', 42, len(username))+username+blob))
                self.assertEqual(result.user_id, 42)
                self.assertEqual(result.username, username)
                self.assertEqual(result.caller_blob, blob)
                self.assertNotIn('username=', repr(result))

    def test_truncated_over_capacity_and_trailing_data(self):
        valid = struct.pack('>II', 42, 0)+bytes(64)
        for body in (b'', valid[:-1], valid+b'x',
                     struct.pack('>II', 42, 33)+bytes(97),
                     struct.pack('>II', 42, 0xffffffff)+bytes(64)):
            with self.assertRaises(ValueError):
                LobbyLoginSuccess.from_frame(Frame(0x120, body))
        with self.assertRaises(ValueError):
            LobbyLoginSuccess.from_frame(Frame(0x601, valid))
