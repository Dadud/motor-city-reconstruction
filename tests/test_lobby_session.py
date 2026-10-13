import unittest

from client.lobby_session import LobbyCiphers
from client.nps_response import SessionKeyRecord
from client.nps_session_request import PreparedLogin


class LobbySessionTests(unittest.TestCase):
    def test_rejects_server_record_and_invalid_retained_key(self):
        with self.assertRaises(TypeError):
            LobbyCiphers.from_login(SessionKeyRecord(bytes(32), 0))
        for material in (b'', bytes(8), bytes(31), bytes(33), 'x'*32):
            with self.assertRaises(ValueError):
                LobbyCiphers.from_login(PreparedLogin(b'', material))

    def test_directions_and_connections_have_independent_zero_iv_chains(self):
        try:
            first = LobbyCiphers.from_login(PreparedLogin(b'', bytes(range(32))))
            second = LobbyCiphers.from_login(PreparedLogin(b'', bytes(range(8))+b'x'*24))
        except ImportError:
            self.skipTest('network dependency not installed')
        block = b'12345678'
        encrypted = first.send.update(block)
        self.assertEqual(second.send.update(block), encrypted)
        self.assertEqual(first.receive.update(encrypted), block)
        self.assertEqual(second.receive.update(encrypted), block)
        self.assertNotIn('send=', repr(first))
        next_block = first.send.update(block)
        self.assertNotEqual(next_block, encrypted)
        self.assertEqual(first.receive.update(next_block), block)
