import socket
import threading
import unittest
from client.mcots_framing import MCOTSFrame
from client.mcots_transport import MCOTSConnection
from client.server_discovery import Endpoint


class MCOTSTransportTests(unittest.TestCase):
    def pair(self):
        local, peer = socket.socketpair()
        connection = MCOTSConnection(local)
        self.addCleanup(connection.close)
        self.addCleanup(peer.close)
        peer.settimeout(2)
        return connection, peer

    def test_fragmented_consecutive_frames(self):
        connection, peer = self.pair()
        frames = (MCOTSFrame(17, 0, b'e\0'), MCOTSFrame(18, 8, b'ciphertext'))
        def produce():
            for byte in b''.join(frame.encode() for frame in frames):
                peer.sendall(bytes((byte,)))
        thread = threading.Thread(target=produce)
        thread.start()
        for frame in frames:
            self.assertEqual(connection.receive(timeout=2), frame)
        thread.join(2)
        self.assertFalse(thread.is_alive())

    def test_invalid_marker_rejected_before_waiting_for_payload(self):
        connection, peer = self.pair()
        peer.sendall(b'\xff\xffFAIL'+bytes(5))
        with self.assertRaises(ValueError):
            connection.receive(timeout=2)
        self.assertEqual(peer.recv(1), b'')

    def test_truncated_and_invalid_frames_close_connection(self):
        for wire in (b'\t\0', b'\x01', MCOTSFrame(17, 0, b'abc').encode()[:-1]):
            connection, peer = self.pair()
            peer.sendall(wire)
            peer.shutdown(socket.SHUT_WR)
            with self.assertRaises((ValueError, EOFError)):
                connection.receive(timeout=2)
            with self.assertRaises(ValueError):
                connection.receive()

    def test_deadline_closes_incomplete_payload(self):
        connection, peer = self.pair()
        peer.sendall(MCOTSFrame(17, 0, b'abc').encode()[:-1])
        with self.assertRaises(TimeoutError):
            connection.receive(timeout=0.05)
        with self.assertRaises(ValueError):
            connection.send(MCOTSFrame(18, 0, b'x').encode())

    def test_validation_preserves_connection(self):
        connection, peer = self.pair()
        for wire in (b'', MCOTSFrame(17, 0, b'x').encode()+b'x'):
            with self.assertRaises(ValueError):
                connection.send(wire)
        for timeout in (0, -1, True, float('nan')):
            with self.assertRaises(ValueError):
                connection.receive(timeout=timeout)
        wire = MCOTSFrame(17, 0, b'e\0').encode()
        connection.send(wire)
        data = bytearray()
        while len(data) < len(wire):
            data.extend(peer.recv(len(wire)-len(data)))
        self.assertEqual(bytes(data), wire)

    def test_real_tcp_connect_and_context_cleanup(self):
        listener = socket.socket()
        self.addCleanup(listener.close)
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        listener.settimeout(2)
        with MCOTSConnection.connect(Endpoint('127.0.0.1', listener.getsockname()[1]), timeout=2) as connection:
            peer, _ = listener.accept()
            self.addCleanup(peer.close)
            peer.settimeout(2)
            frame = MCOTSFrame(17, 0, b'e\0')
            peer.sendall(frame.encode())
            self.assertEqual(connection.receive(timeout=2), frame)
        self.assertEqual(peer.recv(1), b'')
