import struct
import unittest

from client.lobby_response import LobbyLoginSuccess
from client.nps_framing import Frame


class LobbyResponseTests(unittest.TestCase):
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
