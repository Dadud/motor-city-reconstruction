import unittest

from client.track_colors import blend_track_color


class TrackColorTests(unittest.TestCase):
    def test_bypass_returns_the_original_word_unchanged(self):
        self.assertEqual(blend_track_color(0x12345678, 0xabcdef01, 4.0,
                                           bypass=True), 0x12345678)

    def test_blend_sets_opaque_alpha_and_blends_rgb(self):
        self.assertEqual(blend_track_color(0x00102030, 0xffabcdef, 2.0),
                         0xff2f3b48)

    def test_blend_uses_reciprocal_divisor_for_all_channels(self):
        result = blend_track_color(0xff000000, 0xffc86432, 4.0)
        self.assertEqual(result, 0xff190c06)

    def test_rejects_non_word_colors_and_non_boolean_bypass(self):
        for args, kwargs in (((-1, 0, 2.0), {}),
                             ((0, 0x1_0000_0000, 2.0), {}),
                             ((0, 0, 2.0), {'bypass': 1})):
            with self.subTest(args=args, kwargs=kwargs):
                with self.assertRaises(ValueError):
                    blend_track_color(*args, **kwargs)


if __name__ == '__main__':
    unittest.main()
