import unittest

from client.string_compare import compare_config_names


class ConfigNameCompareTests(unittest.TestCase):
    def test_ascii_case_insensitive_and_prefix_order(self):
        self.assertEqual(compare_config_names(b'Garage\0', b'gARAGE\0'), 0)
        self.assertEqual(compare_config_names(b'Alpha\0', b'beta\0'), -1)
        self.assertEqual(compare_config_names(b'bravo\0', b'alpha\0'), 1)
        self.assertEqual(compare_config_names(b'key\0', b'keys\0'), -1)

    def test_non_ascii_bytes_use_wrapped_native_fold(self):
        for first in range(1, 256):
            for second in range(1, 256):
                left, right = bytes((first, 0)), bytes((second, 0))
                folded_left = ((first + 0xbf) & 0xff)
                folded_right = ((second + 0xbf) & 0xff)
                folded_left = (folded_left + (0x20 if folded_left < 0x1a else 0) + 0x41) & 0xff
                folded_right = (folded_right + (0x20 if folded_right < 0x1a else 0) + 0x41) & 0xff
                expected = (folded_left > folded_right) - (folded_left < folded_right)
                self.assertEqual(compare_config_names(left, right), expected)

    def test_requires_terminated_bytes(self):
        with self.assertRaises(ValueError):
            compare_config_names(b'key', b'key\0')
        with self.assertRaises(TypeError):
            compare_config_names('key\0', b'key\0')


if __name__ == '__main__':
    unittest.main()
