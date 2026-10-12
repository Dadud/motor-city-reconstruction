import unittest
from unittest.mock import Mock

from client.lobby_envelope import decrypt_envelope
from client.nps_framing import Frame


class EnvelopeTests(unittest.TestCase):
    def test_outer_body_is_passed_without_twelve_byte_header(self):
        cipher = Mock()
        inner = Frame(0x207, b'abc')
        cipher.update.return_value = inner.encode() + b'\xff'
        result = decrypt_envelope(Frame(0x1101, b'cipher12'), cipher)
        cipher.update.assert_called_once_with(b'cipher12')
        self.assertEqual(result.inner, inner)
        self.assertEqual(result.padding, b'\xff')
        self.assertNotIn('padding=', repr(result))

    def test_outer_validation_precedes_cipher_state_mutation(self):
        cipher = Mock()
        for frame in (Frame(0x501, bytes(8)), Frame(0x1101, b''),
                      Frame(0x1101, bytes(7)), Frame(0x1101, bytes(60000))):
            with self.assertRaises(ValueError):
                decrypt_envelope(frame, cipher)
        cipher.update.assert_not_called()

    def test_bad_inner_lengths(self):
        for output in (b'', bytes.fromhex('02070003')+bytes(4),
                       bytes.fromhex('02070009')+bytes(4),
                       bytes.fromhex('02070004')+bytes(12)):
            cipher = Mock()
            cipher.update.return_value = output
            with self.assertRaises(ValueError):
                decrypt_envelope(Frame(0x1101, bytes(8)), cipher)
