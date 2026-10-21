import unittest

from client.mouse_fallback_state import build_fallback_mouse_outputs


def image(words):
    return b''.join(word.to_bytes(4, 'little') for word in words)


class MouseFallbackStateTests(unittest.TestCase):
    def test_dispatches_first_four_unconditionally_and_later_actions_on_low_byte(self):
        words = (0, 1, 0x101, 0x202, 0x300, 0x401, 0x502, 0x600)
        results = {word: word + 10 for word in words}
        calls = []
        result = build_fallback_mouse_outputs(image(words),
            dispatch_action=lambda action: calls.append(action) or results[action])
        self.assertEqual(calls, list(words[:4]) + [words[5], words[6]])
        self.assertEqual(result.dispatch_trace, tuple(calls))
        self.assertEqual((result.button_state_0, result.button_state_1),
                         ((words[2] + 10) & 0xff, (words[3] + 10) & 0xff))
        self.assertEqual(result.transition_flags, 0x2 | 0x1 | 0x10 | 0x20)

    def test_flag_types_and_first_pair_arithmetic_use_native_byte_and_signed_rules(self):
        words = (0x101, 0x201, 0x304, 0x404, 0x508, 0x610, 0x720, 0x840)
        results = (0xfffffff0, 0x00000020, 0x12345678, 0x87654321,
                   1, 0, 0xffffffff, 0)
        lookup = dict(zip(words, results))
        result = build_fallback_mouse_outputs(image(words),
            dispatch_action=lookup.__getitem__)
        difference = (0x20 - (-16)) >> 1
        self.assertEqual(result.cursor_delta, difference & 0xff)
        self.assertEqual((result.button_state_0, result.button_state_1),
                         (0x78, 0x21))
        self.assertEqual(result.transition_flags, 0x4 | 0x1 | 0x8 | 0x20)

    def test_short_image_requires_exact_action_words(self):
        with self.assertRaises(ValueError):
            build_fallback_mouse_outputs(b'\0' * 28, dispatch_action=lambda _: 0)


if __name__ == '__main__':
    unittest.main()
