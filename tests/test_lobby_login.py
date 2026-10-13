import struct
import unittest
from dataclasses import replace

from client.lobby_login import LobbyLogin, session_key_digest
from client.nps_session_request import PreparedLogin


class LobbyLoginTests(unittest.TestCase):
    def test_selected_persona_uses_zero_blob_and_retained_key_digest(self):
        prepared = PreparedLogin(b'', bytes(range(32)))
        login = LobbyLogin.for_selected_persona(42, b'persona', prepared,
            value_200=7, hostname=b'host', ip_address=b'127.0.0.1')
        self.assertEqual(login.user_id, 42)
        self.assertEqual(login.username, b'persona')
        self.assertEqual(login.key_blob, bytes(64))
        self.assertEqual(login.value_100, 0)
        self.assertEqual(login.value_200, 7)
        self.assertEqual(login.opaque_16, session_key_digest(prepared.session_material))
        self.assertEqual(login.version, b'4.5.0.0')

    def test_retained_key_digest(self):
        self.assertEqual(session_key_digest(bytes(range(32))).hex(),
                         'b4ffcb23737cec315a4a4d1aa2a620ce')
        self.assertEqual(session_key_digest(b'').hex(),
                         'd41d8cd98f00b204e9800998ecf8427e')
        for material in (bytes(33), 'secret', None):
            with self.assertRaises(ValueError):
                session_key_digest(material)

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
