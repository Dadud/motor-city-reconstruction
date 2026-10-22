import unittest

from client.random_state import RandomState


class RandomStateTests(unittest.TestCase):
    def test_native_observed_sequence(self):
        state = RandomState((0xf22d0e56, 0x883126e9, 0xc624dd2f,
                             0x0702c49c, 0x9e353f7d, 0x6fdf3b64))
        self.assertEqual([state.next_u32() for _ in range(4)],
                         [0x559a51ed, 0x274ea7f5, 0xe827f7e0, 0x76b65632])
        self.assertEqual(state.words,
                         (0x76b65632, 0x8e8e5e51, 0xcdb50e66,
                          0xde901484, 0x5db22d13, 0x6fdf3b68))

    def test_wraps_all_six_words(self):
        # Each intermediate sum and the counter wraps, exercising the native
        # post-increment carry propagation special case.
        state = RandomState((0, 0, 0, 0, 0, 0xffffffff))
        state.next_u32()
        self.assertEqual(state.words, (0xffffffff, 0xffffffff, 0xffffffff,
                                       0xffffffff, 0xffffffff, 0))

    def test_rejects_invalid_words(self):
        for words in ((0,) * 5, (0, 0, 0, 0, 0, -1), (0, 0, 0, 0, 0, 1 << 32)):
            with self.subTest(words=words), self.assertRaises(ValueError):
                RandomState(words)


if __name__ == '__main__':
    unittest.main()
