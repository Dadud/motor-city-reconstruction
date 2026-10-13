import struct
import unittest
from dataclasses import replace

from client.lobby_login import LobbyLogin


class LobbyLoginTests(unittest.TestCase):
    def setUp(self):
        self.login = LobbyLogin(42, b'driver', bytes(64), 7, 9, b'4.5.0.0',
                                b'host', b'127.0.0.1', bytes(16))

    def test_string_length_includes_nul_and_frame_has_four_byte_header(self):
        payload = self.login.payload()
        self.assertEqual(payload[:15], bytes.fromhex('0000002a00000007')+b'driver\0')
        frame = self.login.frame().encode()
        self.assertEqual(frame[:4], struct.pack('>HH', 0x100, len(payload)+4))
        self.assertEqual(frame[4:], payload)
        self.assertEqual(self.login.frame(message_id=0x301).body, payload)
        self.assertNotIn('driver', repr(self.login))

    def test_native_buffer_capacities_and_uint32_validation(self):
        for changes in ({'username': b'x'*32}, {'hostname': b'x'*64},
                        {'ip_address': b'x'*16}, {'version': b'x'*32},
                        {'username': b'a\0b'}, {'key_blob': bytes(63)},
                        {'opaque_16': bytes(17)}, {'user_id': -1},
                        {'value_100': 2**32}, {'value_200': True}):
            with self.assertRaises(ValueError):
                replace(self.login, **changes).payload()
        with self.assertRaises(ValueError):
            self.login.frame(message_id=0x501)
