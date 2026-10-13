import socket
import struct
import unittest
from unittest.mock import patch
from client.lobby_connection import connect_lobby, LobbyConnection, LobbyRequestError
from client.lobby_envelope import encrypt_envelope, decrypt_envelope
from client.lobby_login import LobbyLogin
from client.lobby_response import LobbyLoginSuccess, LobbyQueuePosition
from client.lobby_session import LobbyCiphers
from client.nps_framing import Frame
from client.nps_session_request import PreparedLogin
from client.nps_transport import NPSConnection
from client.server_discovery import Endpoint


class LobbyConnectionTests(unittest.TestCase):
    prepared = PreparedLogin(b'', bytes(range(32)))
    success = LobbyLoginSuccess(42, b'name\0', bytes(64))

    def setUp(self):
        try:
            LobbyCiphers.from_login(self.prepared)
        except ImportError:
            self.skipTest('network extra not installed')
        self.login = LobbyLogin.for_selected_persona(42, b'name', self.prepared,
            account_user_id=123, hostname=b'host', ip_address=b'127.0.0.1')

    def success_frame(self):
        return Frame(0x120, struct.pack('>II', 42, 5)+b'name\0'+bytes(64))

    def test_queue_then_plaintext_login_before_persistent_stream(self):
        positions = []
        with patch('client.lobby_connection.NPSConnection.connect') as connect:
            transport = connect.return_value
            transport.receive.side_effect = [Frame(0x231, struct.pack('>HH', 2, 5)),
                Frame(0x230, b''), self.success_frame()]
            connection = connect_lobby(Endpoint('host', 7003), self.login, self.prepared,
                                       on_queue_position=positions.append)
            self.assertEqual(positions, [LobbyQueuePosition(2, 5)])
            transport.send.assert_called_once_with(self.login.frame().encode())
            self.assertEqual(connection.success, self.success)
            transport.close.assert_not_called()
            connection.close()
            connection.close()
            transport.close.assert_called_once()

    def test_rejection_closes_without_login_or_authenticated_stream(self):
        with patch('client.lobby_connection.NPSConnection.connect') as connect:
            transport = connect.return_value
            transport.receive.return_value = Frame(0x21e, b'private version')
            with self.assertRaises(LobbyRequestError) as context:
                connect_lobby(Endpoint('host', 7003), self.login, self.prepared)
            self.assertEqual(context.exception.native_result, -34)
            self.assertNotIn('private', str(context.exception))
            transport.send.assert_not_called()
            transport.close.assert_called_once()
        with patch('client.lobby_connection.NPSConnection.connect') as connect:
            transport = connect.return_value
            transport.receive.return_value = Frame(0x120, b'broken')
            with self.assertRaises(ValueError):
                connect_lobby(Endpoint('host', 7003), self.login, self.prepared, queue_enabled=False)
            transport.close.assert_called_once()

    def pair(self):
        first, second = socket.socketpair()
        local, peer = NPSConnection(first), NPSConnection(second)
        stream = LobbyConnection(local, LobbyCiphers.from_login(self.prepared), self.success)
        self.addCleanup(stream.close)
        self.addCleanup(peer.close)
        return stream, peer, LobbyCiphers.from_login(self.prepared)

    def test_real_socket_cipher_chains_and_plaintext_heartbeat(self):
        stream, peer, remote = self.pair()
        frames = [Frame(0x401, b'one'), Frame(0x402, b'two-message')]
        for frame in frames:
            padding = bytes((-len(frame.encode())) % 8)
            peer.send(encrypt_envelope(frame, remote.send, padding=padding).encode())
            self.assertEqual(stream.receive(timeout=2), frame)
        stream.send(Frame(0x207, b''), padding=b'')
        self.assertEqual(peer.receive(timeout=2), Frame(0x207, b''))
        for frame in frames:
            stream.send(frame, padding=bytes((-len(frame.encode())) % 8))
            self.assertEqual(decrypt_envelope(peer.receive(timeout=2), remote.receive).inner, frame)
        remote.send.finish()
        remote.receive.finish()

    def test_malformed_encrypted_reply_poisoned_stream(self):
        stream, peer, remote = self.pair()
        peer.send(Frame(0x1101, b'not-blocks').encode())
        with self.assertRaises(ValueError):
            stream.receive(timeout=2)
        with self.assertRaises(ValueError):
            stream.receive()
        with self.assertRaises(ValueError):
            stream.send(Frame(0x207, b''), padding=b'')
        remote.send.finish()
        remote.receive.finish()
