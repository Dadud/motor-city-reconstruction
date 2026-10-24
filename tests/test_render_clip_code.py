import unittest

from client.render_clip_code import RenderClipBounds, render_clip_code


class RenderClipCodeTests(unittest.TestCase):
    def setUp(self):
        self.bounds = RenderClipBounds(-100, 100, -80, 80, 1000, -1000)

    def test_inside_and_each_plane(self):
        bounds = self.bounds
        self.assertEqual(render_clip_code((0, 0, -2000, 1), bounds), 0)
        self.assertEqual(render_clip_code((-101, 0, -2000, 1), bounds), 0x10)
        self.assertEqual(render_clip_code((101, 0, -2000, 1), bounds), 0x20)
        self.assertEqual(render_clip_code((0, -81, -2000, 1), bounds), 0x04)
        self.assertEqual(render_clip_code((0, 81, -2000, 1), bounds), 0x08)
        self.assertEqual(render_clip_code((0, 0, -1000, 1), bounds), 0x02)
        self.assertEqual(render_clip_code((0, 0, 0, 1001), bounds), 0x01)

    def test_negative_w_xors_the_original_mask(self):
        self.assertEqual(render_clip_code((0, 0, 0, -1), self.bounds), 0x3d)
        self.assertEqual(render_clip_code((-101, 81, 0, -1), self.bounds),
                         0x25)

    def test_signed_word_domain_is_enforced(self):
        with self.assertRaises(ValueError):
            render_clip_code((0, 0, 0, 1 << 31), self.bounds)
        with self.assertRaises(ValueError):
            RenderClipBounds(0, 1, 0, 1, 0, 1 << 31)


if __name__ == '__main__':
    unittest.main()
