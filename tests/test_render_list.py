import unittest

from client.render_list import RenderRecord, build_render_list


def record(identity, key):
    words = [identity, 0, 0, 0, 0, key, 0, 0, 0]
    return RenderRecord(tuple(words))


class RenderListTests(unittest.TestCase):
    def test_stable_sort_uses_native_record_dword_five(self):
        result = build_render_list((record(0, 0x11), record(1, 0x10),
                                    record(2, 0x10), record(3, 0x12)))
        self.assertEqual([item.words[0] for item in result.records], [3, 0, 1, 2])
        self.assertEqual([item.sort_key for item in result.records],
                         [0x12, 0x11, 0x10, 0x10])

    def test_links_form_null_terminated_chain_after_sort(self):
        result = build_render_list((record(0, 3), record(1, 1), record(2, 2)))
        self.assertEqual(result.next_indices, (1, 2, None))
        self.assertEqual(build_render_list(()).next_indices, ())

    def test_rejects_malformed_native_record_shape(self):
        with self.assertRaises(ValueError):
            RenderRecord((0,) * 8)
        with self.assertRaises(ValueError):
            RenderRecord((0, 0, 0, 0, 0, -1, 0, 0, 0))


if __name__ == '__main__':
    unittest.main()
