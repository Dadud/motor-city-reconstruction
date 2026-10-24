import unittest

from client.string_buffer import BufferRecord, assign_buffer, assign_inline_buffer


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

    def test_empty_unique_releases_and_clears(self):
        old = bytearray([0, *b'abc', 0])
        record = BufferRecord(old, 3, 3)
        released = []
        self.assertEqual(assign_buffer(record, b'', 0, bytearray, released.append), 0)
        self.assertEqual(record, BufferRecord(None, 0, 0))
        self.assertEqual(released, [old])

    def test_shared_assignment_detaches_and_decrements_header(self):
        old = bytearray([2, *b'old', 0])
        record = BufferRecord(old, 3, 3)
        allocations, released = [], []

        def allocate(size):
            allocations.append(size)
            return bytearray(size)

        self.assertEqual(assign_buffer(record, b'new!', 4, allocate, released.append), 4)
        self.assertIsNot(record.storage, old)
        self.assertEqual(record.storage[:6], bytearray([0, *b'new!', 0]))
        self.assertEqual((record.length, record.capacity), (4, 4))
        self.assertEqual(old[0], 1)
        self.assertEqual(allocations, [33])
        self.assertEqual(released, [])

    def test_unique_growth_releases_then_allocates(self):
        old = bytearray([0xff, *b'old', 0])
        record = BufferRecord(old, 3, 3)
        released, allocations = [], []

        def allocate(size):
            allocations.append(size)
            return bytearray(size)

        assign_buffer(record, b'grow', 4, allocate, released.append)
        self.assertEqual(released, [old])
        self.assertEqual(allocations, [33])
        self.assertEqual(record.storage[:6], bytearray([0, *b'grow', 0]))

    def test_shared_empty_only_decrements_reference(self):
        old = bytearray([1, *b'old', 0])
        record = BufferRecord(old, 3, 3)
        released = []
        assign_buffer(record, b'', 0, bytearray, released.append)
        self.assertEqual(old[0], 0)
        self.assertIsNone(record.storage)
        self.assertEqual(released, [])


if __name__ == '__main__':
    unittest.main()
