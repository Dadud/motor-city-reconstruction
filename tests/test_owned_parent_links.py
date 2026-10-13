import struct
import unittest

from client.owned_parent_links import link_owned_parents, select_owned_root


def record(abstract, parent=0, attachment=0, family=0, brand=0, compatible=0, marker=0):
    data = bytearray(1596)
    for offset, value in ((0, abstract), (0x600, parent), (0x61c, attachment),
                          (0x203, family), (0x1e3, brand), (0x14, compatible), (0x5f8, marker)):
        struct.pack_into('<i', data, offset, value)
    return bytes(data)


def integer(slot, offset):
    return struct.unpack_from('<i', slot, offset)[0]


class OwnedParentLinkTests(unittest.TestCase):
    def test_first_top_level_slot_swaps_whole_records(self):
        templates = (record(0), record(10, 2), record(20))
        slots = (record(10, marker=4), record(20, marker=5), record(20, marker=6))
        selected, status = select_owned_root(slots, templates)
        self.assertEqual(status, 1)
        self.assertEqual(selected, (slots[1], slots[0], slots[2]))

    def test_single_slot_and_missing_type_status(self):
        # A valid cache is required even when the original returns early.
        templates = (record(0), record(10))
        self.assertEqual(select_owned_root((record(99),), templates), ((record(99),), 1))
        slots = (record(99), record(10))
        self.assertEqual(select_owned_root(slots, templates), (slots, 3))

    def test_first_duplicate_template_is_used(self):
        templates = (record(0), record(10, 3), record(10), record(20))
        slots = (record(10), record(20))
        self.assertEqual(select_owned_root(slots, templates)[0], (slots[1], slots[0]))

    def test_chassis_fallback_and_distance_strict_ties(self):
        templates = (record(0), record(10, 3), record(1001, 3), record(20))
        slots = (record(10), record(1001))
        self.assertEqual(select_owned_root(slots, templates)[0], (slots[1], slots[0]))
        templates = (record(0), record(10, 3), record(11, 3), record(20))
        slots = (record(10), record(11))
        self.assertEqual(select_owned_root(slots, templates)[0], slots)

    def test_original_255_distance_cap_retains_first_slot(self):
        # A chain ending at an absent chassis: candidates at distances 256 and
        # 255 both fail the initial strict-less-than-255 selection comparison.
        templates = [record(0), record(1001)]
        for distance in range(1, 257):
            templates.append(record(1001 + distance, parent=distance))
        slots = (record(1257), record(1256))
        self.assertEqual(select_owned_root(slots, templates), (slots, 1))

    def test_parent_last_match_wildcard_and_unmatched_preserved(self):
        templates = (record(0), record(10, 2), record(20))
        slots = (record(10, attachment=7, marker=1), record(20, attachment=7, marker=2),
                 record(20, attachment=99, marker=3), record(20, attachment=0, marker=4))
        result = link_owned_parents(slots, templates)
        self.assertEqual(integer(result[1], 0x600), 3)
        self.assertEqual(integer(result[2], 0x600), 0)

    def test_missing_type_does_not_prevent_other_parent_links(self):
        templates = (record(0), record(10, 2), record(20))
        result = link_owned_parents((record(99, parent=1), record(10), record(20)), templates)
        self.assertEqual(integer(result[0], 0x600), 1)
        self.assertEqual(integer(result[1], 0x600), 2)

    def test_last_branded_source_family_overrides_last_target(self):
        templates = (record(0), record(36001), record(160001))
        slots = (record(36001, family=1), record(160001, family=55, brand=3),
                 record(36001, family=2), record(160001, family=66, brand=4),
                 record(160001, family=77, brand=0))
        result = link_owned_parents(slots, templates)
        self.assertEqual(integer(result[0], 0x203), 1)
        self.assertEqual(integer(result[2], 0x203), 66)

    def test_family_fallback_last_compatible_child_and_zero_reset(self):
        templates = (record(0), record(36001), record(10, 1, compatible=1),
                     record(11, 1, compatible=0))
        slots = (record(36001, family=99), record(10, family=44),
                 record(11, family=55), record(10, family=66))
        result = link_owned_parents(slots, templates)
        self.assertEqual(integer(result[0], 0x203), 66)
        self.assertEqual(integer(link_owned_parents((record(36001, family=99),), templates)[0], 0x203), 0)

    def test_only_expected_bytes_change_and_input_immutable(self):
        templates = (record(0), record(10, 2), record(20))
        slots = (record(10, marker=8), record(20, marker=9))
        original = tuple(slots)
        result = link_owned_parents(slots, templates)
        self.assertEqual(slots, original)
        for before, after in zip((slots[1], slots[0]), result):
            self.assertEqual(before[:0x600], after[:0x600])
            self.assertEqual(before[0x604:], after[0x604:])

    def test_unmatched_owned_parent_values_are_preserved_without_dereference(self):
        templates = (record(0), record(10, 2), record(20))
        slots = (record(10, parent=-1, attachment=9), record(20, parent=999, attachment=8))
        selected, status = select_owned_root(slots, templates)
        self.assertEqual((selected, status), ((slots[1], slots[0]), 1))
        self.assertEqual(link_owned_parents(slots, templates), selected)

    def test_invalid_inputs_and_cycles_rejected(self):
        for slots, templates in (
                ([], [record(0)]), ([record(1)], []), ([b'x'], [record(0)]),
                ([record(1)], [record(1)]), ([record(1)], [record(0), record(1, -1)]),
                ([record(1)], [record(0), record(1, 2)]),
                ([record(1)], [record(0), record(1, 1)]),
                ([record(1)], [record(0), record(1, 2), record(2, 1)])):
            with self.subTest(count=len(slots)):
                with self.assertRaises(ValueError):
                    select_owned_root(slots, templates)
                with self.assertRaises(ValueError):
                    link_owned_parents(slots, templates)


if __name__ == '__main__':
    unittest.main()
