import unittest

from client.render_state import (RenderCapabilityState, set_capability_2,
                                 set_capability_4, set_vertex_format_cache)


class RenderCapabilityStateTests(unittest.TestCase):
    def test_capability_setters_keep_nonzero_mode_cache_and_mark_dirty(self):
        state = RenderCapabilityState(mode_cache=9)
        old, state = set_capability_4(state, 7)
        self.assertEqual(old, 0)
        self.assertEqual((state.capability_4, state.capability_4_dirty,
                          state.mode_cache), (7, 1, 9))
        old, state = set_capability_2(state, 3)
        self.assertEqual(old, 0)
        self.assertEqual((state.capability_2, state.capability_2_dirty,
                          state.mode_cache), (3, 1, 9))

    def test_zero_capability_and_format_invalidate_mode_cache(self):
        state = RenderCapabilityState(capability_4=2, capability_2=3,
                                      mode_cache=8, vertex_format_cache=4)
        _, state = set_capability_4(state, 0)
        self.assertEqual(state.mode_cache, 0xffffffff)
        _, state = set_vertex_format_cache(state, 0)
        self.assertEqual((state.vertex_format_cache, state.mode_cache),
                         (0, 0xffffffff))

    def test_format_setter_returns_previous_cache(self):
        state = RenderCapabilityState(vertex_format_cache=0x11, mode_cache=5)
        old, state = set_vertex_format_cache(state, 0x22)
        self.assertEqual((old, state.vertex_format_cache, state.mode_cache),
                         (0x11, 0x22, 5))


if __name__ == '__main__':
    unittest.main()
