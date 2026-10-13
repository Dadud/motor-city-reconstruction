import struct
import unittest

from client.owned_ordering import order_owned_candidates, reorder_owned_parts


def record(abstract, parent=0, attachment=0, marker=1):
    output = bytearray([marker] * 1596)
    for offset, value in ((0, abstract), (0x600, parent), (0x61c, attachment)):
        struct.pack_into('<i', output, offset, value)
    return bytes(output)


class OwnedOrderingTests(unittest.TestCase):
    def test_exact_attachment_sequence_and_whole_records(self):
        attachments = (0, 9, 8, 7, 6, 4, 3, 11, 5, 2, 1, 10)
        slots = tuple(record(101, attachment=value, marker=index + 1)
                      for index, value in enumerate(attachments))
        templates = (record(0), record(101))
        expected = tuple(slots[attachments.index(value)]
                         for value in (10, 1, 2, 5, 11, 3, 4, 6, 7, 8, 9, 0))
        self.assertEqual(order_owned_candidates(slots, templates), expected)
        self.assertEqual(reorder_owned_parts(slots, templates), expected)

    def test_depth_first_cache_child_order_and_missing_owned_types(self):
        templates = (record(0), record(101), record(10, 1), record(11, 1), record(12, 2))
        slots = (record(101), record(11), record(12), record(10))
        self.assertEqual(order_owned_candidates(slots, templates),
                         (slots[0], slots[3], slots[2], slots[1]))
        # A cache-only intermediate still traverses its own children.
        source = (slots[0], slots[1], slots[2])
        self.assertEqual(order_owned_candidates(source, templates),
                         (source[0], source[2], source[1]))

    def test_unsupported_attachment_and_duplicate_pairs_fail_count_gate(self):
        templates = (record(0), record(101))
        source = (record(101, marker=2), record(101, marker=3), record(101, attachment=99))
        self.assertEqual(order_owned_candidates(source, templates), (source[0],))
        self.assertEqual(reorder_owned_parts(source, templates), source)

    def test_repeated_type_visits_repeat_first_match_and_count_gate_accepts(self):
        templates = (record(0), record(101), record(10, 1), record(10, 1))
        source = (record(101), record(10, marker=22), record(10, marker=33))
        expected = (source[0], source[1], source[1])
        self.assertEqual(order_owned_candidates(source, templates), expected)
        self.assertEqual(reorder_owned_parts(source, templates), expected)

    def test_first_matching_cache_index_controls_children(self):
        templates = (record(0), record(101), record(10, 1), record(10, 1),
                     record(11, 2), record(12, 3))
        source = (record(101), record(10), record(11), record(12))
        self.assertEqual(order_owned_candidates(source, templates),
                         (source[0], source[1], source[2], source[1], source[2]))
        self.assertEqual(reorder_owned_parts(source, templates), source)

    def test_abstract_zero_and_missing_lookup_have_no_children(self):
        templates = (record(0), record(101), record(10, 1))
        source = (record(0, parent=-1), record(10, parent=999))
        self.assertEqual(order_owned_candidates(source, templates), (source[0],))
        source = (record(999, parent=-1), record(10, parent=999))
        self.assertEqual(order_owned_candidates(source, templates), (source[0],))

    def test_empty_inputs_and_inputs_remain_unchanged(self):
        templates = (record(0), record(101))
        self.assertEqual(order_owned_candidates([], templates), ())
        self.assertEqual(reorder_owned_parts([], templates), ())
        source = [record(101, parent=-1)]
        before = tuple(source)
        self.assertEqual(order_owned_candidates(source, templates), before)
        self.assertEqual(tuple(source), before)

    def test_deep_cache_only_intermediates_use_iterative_traversal(self):
        templates = (record(0),) + tuple(record(100 + index, parent=index - 1)
                                         for index in range(1, 1101))
        source = (record(101), record(1200))
        self.assertEqual(order_owned_candidates(source, templates), source)

    def test_duplicate_dag_without_output_has_independent_visit_limit(self):
        templates = [record(0), record(101)]
        previous_first = 1
        for abstract in range(200, 217):
            first = len(templates)
            templates.extend((record(abstract, parent=previous_first),
                              record(abstract, parent=previous_first)))
            previous_first = first
        with self.assertRaisesRegex(ValueError, 'traversal limit'):
            order_owned_candidates((record(101),), templates)

    def test_limits_cycles_and_invalid_records(self):
        templates = (record(0), record(101), record(10, 1), record(10, 1))
        source = (record(101), record(10))
        with self.assertRaises(ValueError):
            order_owned_candidates(source, templates, max_parts=2)
        for max_parts in (0, -1, True):
            with self.assertRaises(ValueError):
                order_owned_candidates(source, templates, max_parts=max_parts)
        for slots, cache in ((None, templates), ([b'x'], templates),
                             ([], (record(0), record(101, parent=-1))),
                             ([record(101)], (record(0), record(101, parent=1)))):
            with self.subTest(slots=type(slots)):
                with self.assertRaises(ValueError):
                    order_owned_candidates(slots, cache)


if __name__ == '__main__':
    unittest.main()
