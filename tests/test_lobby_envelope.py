import unittest
from unittest.mock import Mock

from client.lobby_envelope import decrypt_envelope, encrypt_envelope, native_encrypts_message
from client.nps_framing import Frame


class EnvelopeTests(unittest.TestCase):
    def test_send_preserves_explicit_padding_and_four_byte_wrapper(self):
        cipher = Mock()
        cipher.update.return_value = b'cipher12'
        result = encrypt_envelope(Frame(0x601, b'abc'), cipher, padding=b'\xff')
        cipher.update.assert_called_once_with(bytes.fromhex('06010007')+b'abc\xff')
        self.assertEqual(result.encode(), bytes.fromhex('1101000c')+b'cipher12')

    def test_invalid_send_does_not_advance_cipher(self):
        cipher = Mock()
        for inner, padding in ((None, b''), (Frame(1, b'a'), b''),
                               (Frame(1, b''), bytes(12)),
                               (Frame(1, bytes(59996)), b'')):
            with self.assertRaises(ValueError):
                encrypt_envelope(inner, cipher, padding=padding)
        cipher.update.assert_not_called()

    def test_heartbeat_selector(self):
        self.assertFalse(native_encrypts_message(0x207))
        self.assertFalse(native_encrypts_message(0x217))
        self.assertTrue(native_encrypts_message(0x501))
        with self.assertRaises(ValueError):
            native_encrypts_message(65536)

    def test_multiple_messages_preserve_cbc_chain_and_opaque_tail(self):
        try:
            from client.lobby_cipher import DESChaining
            sender = DESChaining(b'12345678')
            receiver = DESChaining(b'12345678', decrypt=True)
        except ImportError:
            self.skipTest('network dependency not installed')
        for inner, padding in ((Frame(0x601, b'abc'), b'\xff'),
                               (Frame(0x602, b'1234'), b''),
                               (Frame(0x603, b''), b'abcd')):
            result = decrypt_envelope(encrypt_envelope(inner, sender, padding=padding), receiver)
            self.assertEqual(result.inner, inner)
            self.assertEqual(result.padding, padding)
        self.assertEqual(sender.finish(), b'')
        self.assertEqual(receiver.finish(), b'')

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
