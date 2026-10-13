import socket
import struct
import unittest
from client.mcots_cipher import MCOTSCipher
from client.mcots_framing import MCOTSFrame
from client.mcots_session import MCOTSSession
from client.mcots_transport import MCOTSConnection


class MCOTSSessionTests(unittest.TestCase):
    KEY = bytes(range(32))

    def pair(self):
        local, remote = socket.socketpair()
        session = MCOTSSession(MCOTSConnection(local), self.KEY)
        peer = MCOTSConnection(remote)
        self.addCleanup(session.close)
        self.addCleanup(peer.close)
        return session, peer

    def test_encryption_stays_enabled_when_next_frame_has_no_flag(self):
        session, peer = self.pair()
        cipher = MCOTSCipher(self.KEY[:16])
        peer.send(MCOTSFrame(17, 8, cipher.transform(b'first')).encode())
        peer.send(MCOTSFrame(18, 0, cipher.transform(b'second')).encode())
        self.assertEqual(session.receive(timeout=2), MCOTSFrame(17, 0, b'first'))
        self.assertEqual(session.receive(timeout=2), MCOTSFrame(18, 0, b'second'))

    def test_decrypt_then_decompress(self):
        session, peer = self.pair()
        cipher = MCOTSCipher(self.KEY[:16])
        compressed = struct.pack('<H', 13)+bytes.fromhex('00048224258f807f')
        peer.send(MCOTSFrame(17, 10, cipher.transform(compressed)).encode())
        self.assertEqual(session.receive(timeout=2), MCOTSFrame(17, 0, b'AIAIAIAIAIAIA'))

    def test_keepalive_reply_bypasses_cipher_and_preserves_both_streams(self):
        session, peer = self.pair()
        session.enable_encryption()
        incoming = MCOTSCipher(self.KEY[:16])
        peer.send(MCOTSFrame(17, 0x80, struct.pack('<I', 0xf216)).encode())
        peer.send(MCOTSFrame(18, 0, incoming.transform(b'application')).encode())
        self.assertEqual(session.receive(timeout=2), MCOTSFrame(18, 0, b'application'))
        self.assertEqual(peer.receive(timeout=2), MCOTSFrame(17, 0x80, struct.pack('<I', 0xf207)))
        session.send(MCOTSFrame(19, 0, b'outgoing'))
        frame = peer.receive(timeout=2)
        self.assertEqual(frame.flags, 8)
        self.assertEqual(MCOTSCipher(self.KEY[:16]).transform(frame.payload), b'outgoing')

    def test_plain_attachment_then_explicit_activation(self):
        session, peer = self.pair()
        session.send(MCOTSFrame(0, 0, b'attachment'))
        self.assertEqual(peer.receive(timeout=2), MCOTSFrame(0, 0, b'attachment'))
        session.enable_encryption()
        cipher = MCOTSCipher(self.KEY[:16])
        for transaction, payload in ((1, b'login'), (2, b'next')):
            session.send(MCOTSFrame(transaction, 0, payload))
            frame = peer.receive(timeout=2)
            self.assertEqual(cipher.transform(frame.payload), payload)

    def test_bad_compressed_reply_closes_everything(self):
        session, peer = self.pair()
        peer.send(MCOTSFrame(17, 2, b'bad').encode())
        with self.assertRaises(ValueError):
            session.receive(timeout=2)
        self.assertTrue(session._incoming._closed)
        self.assertTrue(session._outgoing._closed)
        with self.assertRaises(ValueError):
            session.send(MCOTSFrame(18, 0, b'x'))

    def test_invalid_send_does_not_advance_cipher(self):
        session, peer = self.pair()
        session.enable_encryption()
        with self.assertRaises(ValueError):
            session.send(MCOTSFrame(17, 8, b'x'))
        with self.assertRaises(ValueError):
            session.send(MCOTSFrame(17, 0, b'x'), timeout=0)
        session.send(MCOTSFrame(17, 0, b'x'))
        frame = peer.receive(timeout=2)
        self.assertEqual(MCOTSCipher(self.KEY[:16]).transform(frame.payload), b'x')
