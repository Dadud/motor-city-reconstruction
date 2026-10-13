import struct
import unittest

from client.owned_dependencies import link_owned_dependencies


def slot(abstract=101, attachment=10, parent=0, dependency=77, flag=91, owned_id=1):
    data = bytearray([0xa5] * 1596)
    for offset, value in ((0, abstract), (0x600, parent), (0x604, dependency),
                          (0x61c, attachment), (0x634, flag)):
        struct.pack_into('<i', data, offset, value)
    struct.pack_into('<I', data, 0x5f8, owned_id)
    return bytes(data)


def integer(data, offset):
    return struct.unpack_from('<i', data, offset)[0]


class OwnedDependencyTests(unittest.TestCase):
    def test_last_matching_candidate_and_attachment_wildcard(self):
        source = (slot(), slot(500, 10), slot(500, 99), slot(500, 0))
        result = link_owned_dependencies(source, (500, 0, 0, 0))
        self.assertEqual(integer(result[0], 0x604), 3)
        self.assertEqual(integer(result[0], 0x634), 91)
        # A mismatched nonzero attachment must not supersede the earlier match.
        result = link_owned_dependencies(source[:3], (500, 0, 0))
        self.assertEqual(integer(result[0], 0x604), 1)

    def test_no_match_preserves_index_and_zero_id_clears(self):
        source = (slot(dependency=-123), slot(500, 99, dependency=99))
        result = link_owned_dependencies(source, (500, 0))
        self.assertEqual(integer(result[0], 0x604), -123)
        self.assertEqual(integer(result[1], 0x604), 0)

    def test_self_matches_and_signed_abstract_attachment_ids(self):
        source = (slot(-1, -10), slot(-1, -10))
        result = link_owned_dependencies(source, (-1, -1))
        self.assertEqual(tuple(integer(value, 0x604) for value in result), (1, 1))

    def test_flag_clear_rules_and_preserved_unrelated_slot(self):
        source = (slot(), slot(2001), slot(20001), slot(6001),
                  slot(44, parent=3), slot(45))
        result = link_owned_dependencies(source, (0,) * len(source))
        self.assertEqual(tuple(integer(value, 0x634) for value in result),
                         (91, 0, 0, 0, 0, 91))

    def test_missing_owned_root_clears_all_flags(self):
        source = (slot(owned_id=0), slot(), slot())
        result = link_owned_dependencies(source, (0, 0, 0))
        self.assertEqual(tuple(integer(value, 0x634) for value in result), (0, 0, 0))

    def test_only_dependency_and_flag_fields_change_without_mutating_input(self):
        source = [slot(), slot(2001)]
        original = tuple(source)
        result = link_owned_dependencies(source, [0, 0])
        self.assertIsInstance(result, tuple)
        self.assertEqual(tuple(source), original)
        for before, after in zip(source, result):
            for index in range(1596):
                if not (0x604 <= index < 0x608 or 0x634 <= index < 0x638):
                    self.assertEqual(before[index], after[index])

    def test_invalid_slots_dependency_values_and_parent_indexes_rejected(self):
        for slots, dependencies in (
                ([], []), (None, []), ([b'x'], [0]), ([bytearray(slot())], [0]),
                ([slot()], []), ([slot()], None), ([slot()], [True]),
                ([slot()], [2**31]), ([slot()], [-2**31 - 1]),
                ([slot(parent=-1)], [0]), ([slot(parent=1)], [0]),
                ([slot(parent=-1, owned_id=0)], [0])):
            with self.subTest(slots=type(slots), dependencies=dependencies):
                with self.assertRaises(ValueError):
                    link_owned_dependencies(slots, dependencies)


if __name__ == '__main__':
    unittest.main()
