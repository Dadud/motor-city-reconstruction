import socket
import struct
import threading
import unittest
from unittest.mock import patch
from client.mcots_attachment import MCOTSAttachment
from client.mcots_cipher import MCOTSCipher
from client.mcots_framing import MCOTSFrame
from client.mcots_login import MCOTSLoginRecord
from client.mcots_primary_service import connect_primary, MCOTSPrimaryRejected
from client.mcots_transport import MCOTSConnection
from client.server_discovery import Endpoint


class MCOTSPrimaryServiceTests(unittest.TestCase):
    KEY = bytes(range(32))
    RECORD = MCOTSLoginRecord(123, 42, b'persona', 11, 22, 33)

    def run_peer(self, behavior, **kwargs):
        listener = socket.socket()
        self.addCleanup(listener.close)
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        listener.settimeout(2)
        errors = []
        def serve():
            try:
                sock, _ = listener.accept()
                with MCOTSConnection(sock) as peer:
                    behavior(peer)
            except Exception as error:
                errors.append(error)
        thread = threading.Thread(target=serve)
        thread.start()
        result = error = None
        try:
            result = connect_primary(Endpoint('127.0.0.1', listener.getsockname()[1]),
                                     self.RECORD, self.KEY, connect_timeout=2,
                                     attachment_timeout=2, login_timeout=2, **kwargs)
        except Exception as caught:
            error = caught
        if result:
            result.close()
        thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        return result, error

    def test_complete_plain_attachment_then_encrypted_login_and_keepalive(self):
        def peer(connection):
            attachment = connection.receive(timeout=2)
            self.assertEqual(attachment, MCOTSFrame(0xffffffff, 0, MCOTSAttachment(123, 42, b'persona').encode()))
            connection.send(MCOTSFrame(attachment.transaction_value, 0, b'e\0').encode())
            login = connection.receive(timeout=2)
            self.assertEqual((login.transaction_value, login.flags), (0, 8))
            self.assertEqual(MCOTSCipher(self.KEY[:16]).transform(login.payload), self.RECORD.encode_native_record())
            connection.send(MCOTSFrame(9, 0x80, struct.pack('<I', 0xf216)).encode())
            response = bytearray(173)
            struct.pack_into('<HI', response, 0, 0xd5, 12345)
            for index in range(4):
                struct.pack_into('<I', response, 33+26*index, 0xff)
            encrypted = MCOTSCipher(self.KEY[:16]).transform(bytes(response))
            connection.send(MCOTSFrame(login.transaction_value, 8, encrypted).encode())
            self.assertEqual(connection.receive(timeout=2), MCOTSFrame(9, 0x80, struct.pack('<I', 0xf207)))
            self.assertEqual(connection._socket.recv(1), b'')
        result, error = self.run_peer(peer, first_transaction=0xffffffff)
        self.assertIsNone(error)
        self.assertEqual(result.response.session_value, 12345)

    def test_rejection_closes_without_sending_login(self):
        def peer(connection):
            request = connection.receive(timeout=2)
            connection.send(MCOTSFrame(request.transaction_value, 0,
                                      struct.pack('<HHI', 0x66, 0x1b6, 0x83)).encode())
            self.assertEqual(connection._socket.recv(1), b'')
        result, error = self.run_peer(peer)
        self.assertIsNone(result)
        self.assertIsInstance(error, MCOTSPrimaryRejected)
        self.assertEqual((error.stage, error.result_code), ('attachment', 0x83))

    def test_wrong_attachment_transaction_closes_without_login(self):
        def peer(connection):
            connection.receive(timeout=2)
            connection.send(MCOTSFrame(99, 0, b'e\0').encode())
            self.assertEqual(connection._socket.recv(1), b'')
        result, error = self.run_peer(peer)
        self.assertIsNone(result)
        self.assertIsInstance(error, ValueError)

    def test_validation_precedes_socket_connect(self):
        with patch.object(MCOTSConnection, 'connect') as connect:
            for material in (b'', bytes(31)):
                with self.assertRaises(ValueError):
                    connect_primary(Endpoint('localhost', 43300), self.RECORD, material)
            with self.assertRaises(ValueError):
                connect_primary(Endpoint('localhost', 43300), self.RECORD, self.KEY, login_timeout=0)
            connect.assert_not_called()

    def test_incomplete_or_mismatched_login_reply_never_returns_primary_login(self):
        for payload, transaction in ((b'e\0', 1), (b'\xd5\0', 1),
                                     (b'\xd5\0'+bytes(171), 99)):
            def peer(connection):
                attachment = connection.receive(timeout=2)
                connection.send(MCOTSFrame(attachment.transaction_value, 0, b'e\0').encode())
                connection.receive(timeout=2)
                ciphertext = MCOTSCipher(self.KEY[:16]).transform(payload)
                connection.send(MCOTSFrame(transaction, 8, ciphertext).encode())
                self.assertEqual(connection._socket.recv(1), b'')
            result, error = self.run_peer(peer)
            self.assertIsNone(result)
            self.assertIsInstance(error, ValueError)
