import unittest

from client.string_buffer import assign_inline_buffer


class StringBufferTests(unittest.TestCase):
    def test_assignment_copies_exact_length_and_terminates(self):
        destination = bytearray(b'abcdefgh\xff')
        self.assertEqual(assign_inline_buffer(destination, b'xy\x00z', 4, 8), 4)
        self.assertEqual(destination, b'xy\x00z\x00fgh\xff')

    def test_word_and_tail_lengths(self):
        for length in range(1, 17):
            with self.subTest(length=length):
                destination = bytearray([0xa5] * 18)
                source = bytes(range(18))
                self.assertEqual(assign_inline_buffer(destination, source, length, 17), length)
                self.assertEqual(destination[:length], source[:length])
                self.assertEqual(destination[length], 0)

    def test_rejects_non_inline_or_empty_paths(self):
        with self.assertRaisesRegex(ValueError, 'in-place path'):
            assign_inline_buffer(bytearray(33), b'x', 0, 31)
        with self.assertRaisesRegex(ValueError, 'in-place path'):
            assign_inline_buffer(bytearray(33), bytes(33), 32, 32)
        with self.assertRaisesRegex(ValueError, 'in-place path'):
            assign_inline_buffer(bytearray(5), b'abcdef', 6, 4)


if __name__ == '__main__':
    unittest.main()
