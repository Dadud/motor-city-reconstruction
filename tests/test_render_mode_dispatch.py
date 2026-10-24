import unittest

from client.render_mode_dispatch import RenderDispatchState, dispatch_render_mode


def state(**overrides):
    values = dict(cached_mode=0xffffffff, capability_bit_4=1,
        capability_bit_2=1, capability_bit_0x10000=1,
        capability_bit_0x20000_a=1, capability_bit_0x20000_b=1,
        capability_both_0x30000=1, capability_bit0=1, callback_context_b=0x77,
        vertex_stride=0, vertex_format=0, primary_callbacks=(1,)*32,
        secondary_callbacks=(1,)*8)
    values.update(overrides)
    return RenderDispatchState(**values)


class RenderDispatchTests(unittest.TestCase):
    def test_filters_flags_defaults_layout_and_records_both_callbacks(self):
        before = state(capability_bit_4=0, capability_bit_2=0,
                       capability_bit_0x10000=0, capability_bit0=0)
        result, after, events = dispatch_render_mode(before, 0x30007, 5, 0x1000, 0x2000)
        self.assertEqual(result, 0)
        self.assertEqual(after.cached_mode, result)
        self.assertEqual((after.vertex_stride, after.vertex_format), (12, 32))
        self.assertEqual(after.draw_context_b, 0x77)
        self.assertEqual(events, (('primary', 5, 0x1000, 0x2000),))

    def test_same_mode_uses_cached_callbacks_without_refiltering(self):
        before = state(cached_mode=0x30000, capability_bit_4=0,
                       primary_callbacks=(0,)*32, secondary_callbacks=(0,)*8,
                       primary_callback=1, secondary_callback=1)
        result, _, events = dispatch_render_mode(before, 0x30000, 4, 0x100, 0x200)
        self.assertEqual(result, 0x30000)
        self.assertEqual(events, (('primary', 4, 0x100, 0x200),
                                  ('secondary', 4, 0x200)))

    def test_invalid_draw_arguments_return_zero_without_callbacks(self):
        before = state()
        result, after, events = dispatch_render_mode(before, 1, 0, 0x100, 0x200)
        self.assertEqual(result, 0)
        self.assertEqual(events, ())
        self.assertEqual(after.cached_mode, 1)

    def test_rejects_malformed_callback_tables(self):
        with self.assertRaises(ValueError):
            state(primary_callbacks=(1,))


if __name__ == '__main__':
    unittest.main()


