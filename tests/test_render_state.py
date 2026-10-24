import unittest

from client.render_state import (replace_render_mode,
                                 select_rectangle_texture_state)


class RenderStateTests(unittest.TestCase):
    def test_replacing_mode_returns_old_word_and_updates_mode(self):
        self.assertEqual(replace_render_mode(0x1234, 0x8765, 0x20000),
                         (0x1234, 0x20000, 0x8765))

    def test_zero_mode_invalidates_dependent_cache(self):
        self.assertEqual(replace_render_mode(0x1234, 0x8765, 0),
                         (0x1234, 0, 0xffffffff))

    def test_preserves_zero_cache_for_nonzero_mode(self):
        self.assertEqual(replace_render_mode(0xffffffff, 0, 1),
                         (0xffffffff, 1, 0))

    def test_rejects_values_outside_unsigned_word_domain(self):
        for value in (-1, 0x100000000, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                replace_render_mode(value, 0, 1)

    def test_rectangle_state_selection_skips_callback_on_cache_hit(self):
        self.assertEqual(select_rectangle_texture_state(0),(0,()))

    def test_rectangle_state_selection_clears_nonzero_cache(self):
        self.assertEqual(select_rectangle_texture_state(0x1234),(0,(0,)))


if __name__ == '__main__':
    unittest.main()
