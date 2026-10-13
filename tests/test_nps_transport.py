import socket
import threading
import unittest
from unittest.mock import patch
from client.nps_framing import Frame
from client.nps_transport import NPSConnection, query
from client.server_discovery import Endpoint


class NPSTransportTests(unittest.TestCase):
    def pair(self):
        local, peer = socket.socketpair()
        connection = NPSConnection(local)
        self.addCleanup(connection.close)
        self.addCleanup(peer.close)
        peer.settimeout(2)
        return connection, peer

    def test_fragmentation_and_consecutive_messages(self):
        connection, peer = self.pair()
        first, second = Frame(0x607, b'persona-map'), Frame(0x207, b'')
        wire = first.encode()+second.encode()
        def produce():
            for byte in wire:
                peer.sendall(bytes([byte]))
        thread = threading.Thread(target=produce)
        thread.start()
        self.assertEqual(connection.receive(timeout=2), first)
        self.assertEqual(connection.receive(timeout=2), second)
        thread.join(2)
        self.assertFalse(thread.is_alive())

    def test_send_exact_bytes(self):
        connection, peer = self.pair()
        wire = Frame(0x503, bytes(range(12))).encode()
        connection.send(wire)
        received = bytearray()
        while len(received) < len(wire):
            received.extend(peer.recv(len(wire)-len(received)))
        self.assertEqual(received, wire)

    def test_invalid_lengths_close_stream(self):
        for wire in (b'\x06\x07\0\x03', b'\x06', b'\x06\x07\0\x08abc'):
            connection, peer = self.pair()
            peer.sendall(wire)
            peer.shutdown(socket.SHUT_WR)
            with self.assertRaises((ValueError, EOFError)):
                connection.receive(timeout=2)
            with self.assertRaises(ValueError):
                connection.receive()

    def test_deadline_closes_incomplete_body(self):
        connection, peer = self.pair()
        peer.sendall(b'\x06\x07\0\x08a')
        with self.assertRaises(TimeoutError):
            connection.receive(timeout=0.1)
        with self.assertRaises(ValueError):
            connection.send(Frame(0x532, b'').encode())

    def test_invalid_requests_are_not_sent(self):
        connection, peer = self.pair()
        for wire in (b'', b'\0\1\0\x05', b'\0\1\0\x04extra'):
            with self.assertRaises(ValueError):
                connection.send(wire)
        for value in (0, -1, float('nan'), float('inf'), True):
            with self.assertRaises(ValueError):
                connection.receive(timeout=value)
        # Validation failures leave the connection usable.
        connection.send(Frame(0x532, b'').encode())
        self.assertEqual(peer.recv(4), b'\x05\x32\0\x04')

    def test_fresh_request_connection_closes_after_reply(self):
        listener = socket.socket()
        self.addCleanup(listener.close)
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        listener.settimeout(2)
        request = Frame(0x532, b'account').encode()
        reply = Frame(0x607, b'records')
        observed = []
        errors = []
        def server():
            try:
                sock, _ = listener.accept()
                with sock:
                    sock.settimeout(2)
                    data = bytearray()
                    while len(data) < len(request):
                        part = sock.recv(len(request)-len(data))
                        if not part:
                            raise EOFError('missing test request')
                        data.extend(part)
                    observed.append(bytes(data))
                    sock.sendall(reply.encode())
                    observed.append(sock.recv(1))
            except Exception as error:
                errors.append(error)
        thread = threading.Thread(target=server)
        thread.start()
        result = query(Endpoint('127.0.0.1', listener.getsockname()[1]), request,
                       connect_timeout=2, receive_timeout=2)
        thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(result, reply)
        self.assertEqual(observed, [request, b''])

    def test_query_validation_precedes_connection(self):
        with patch.object(NPSConnection, 'connect') as connect:
            with self.assertRaises(ValueError):
                query(Endpoint('localhost', 8228), b'bad')
            with self.assertRaises(ValueError):
                query(Endpoint('localhost', 8228), Frame(0x503, b'').encode(),
                      receive_timeout=0)
            connect.assert_not_called()
