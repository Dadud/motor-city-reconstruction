import unittest
from client.mcots_cipher import MCOTSCipher


class MCOTSCipherTests(unittest.TestCase):
    def test_persistent_stream_and_independent_directions(self):
        key = bytes(range(16))
        data = bytes(range(256))*3
        whole = MCOTSCipher(key).transform(data)
        split = MCOTSCipher(key)
        self.assertEqual(split.transform(data[:39])+split.transform(data[39:]), whole)
        self.assertEqual(MCOTSCipher(key).transform(whole), data)
        self.assertNotEqual(whole[:39], split.transform(data[:39]))

    def test_rejected_input_preserves_state(self):
        cipher = MCOTSCipher(bytes(16))
        for invalid in ('x', b'x'*65527):
            with self.assertRaises(ValueError):
                cipher.transform(invalid)
        self.assertEqual(cipher.transform(b''), b'')
        self.assertEqual(cipher.transform(b'hello'), MCOTSCipher(bytes(16)).transform(b'hello'))
        cipher.close()
        with self.assertRaises(ValueError):
            cipher.transform(b'hello')

    def test_key_length(self):
        for invalid in (b'', bytes(15), bytes(17), '0123456789abcdef'):
            with self.assertRaises(ValueError):
                MCOTSCipher(invalid)
