import importlib.util
import unittest

from client.lobby_cipher import DESChaining


@unittest.skipUnless(importlib.util.find_spec('cryptography'), 'optional network cryptography')
class ChainingTests(unittest.TestCase):
    def test_standard_first_block_and_chaining_across_updates(self):
        key = bytes.fromhex('133457799BBCDFF1')
        block = bytes.fromhex('0123456789ABCDEF')
        first = DESChaining(key)
        encrypted = first.update(block)
        self.assertEqual(encrypted.hex(), '85e813540f0ab405')
        encrypted += first.update(block)
        self.assertEqual(first.finish(), b'')
        together = DESChaining(key).update(block*2)
        self.assertEqual(encrypted, together)
        decoder = DESChaining(key, decrypt=True)
        self.assertEqual(decoder.update(encrypted[:8]) + decoder.update(encrypted[8:]), block*2)
        decoder.finish()

    def test_reject_partial_blocks_and_closed_state(self):
        cipher = DESChaining(bytes(8))
        with self.assertRaises(ValueError):
            cipher.update(b'x')
        self.assertEqual(cipher.update(b''), b'')
        cipher.finish()
        with self.assertRaises(ValueError):
            cipher.update(bytes(8))

    def test_key_and_iv_bounds(self):
        for key, iv in ((bytes(7), bytes(8)), (bytes(9), bytes(8)), (bytes(8), bytes(7))):
            with self.assertRaises(ValueError):
                DESChaining(key, iv=iv)
