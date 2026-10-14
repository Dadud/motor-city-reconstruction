import unittest

from client.lobby_cipher import DESChaining
from client.lobby_envelope import decrypt_envelope
from client.lobby_send import prepare_outgoing_frame
from client.lobby_session import LobbyCiphers
from client.nps_framing import Frame


class LobbySendTests(unittest.TestCase):
    def test_plaintext_heartbeat_is_not_wrapped(self):
        ciphers = LobbyCiphers(DESChaining(b'12345678'), DESChaining(b'12345678', decrypt=True))
        frame = Frame(0x207, b'')
        outgoing = prepare_outgoing_frame(frame, ciphers, padding=b'')
        self.assertEqual(outgoing, frame)

    def test_application_frame_is_wrapped(self):
        ciphers = LobbyCiphers(DESChaining(b'12345678'), DESChaining(b'12345678', decrypt=True))
        inner = Frame(0x601, b'abc')
        padding = bytes((-len(inner.encode())) % 8)
        outgoing = prepare_outgoing_frame(inner, ciphers, padding=padding)
        self.assertEqual(outgoing.message_id, 0x1101)
        decoded = decrypt_envelope(outgoing, ciphers.receive)
        self.assertEqual(decoded.inner, inner)


if __name__ == '__main__':
    unittest.main()

