import struct
import unittest

from client.part_type_templates import build_part_type_cache, resolve_part_type_cache


def record(identifier, parent=0, dependency=0, parent_index=-1, depends_index=-1):
    data = bytearray(b'\xa5' * 1596)
    struct.pack_into('<iii', data, 0, identifier, parent, dependency)
    struct.pack_into('<ii', data, 0x600, parent_index, depends_index)
    return bytes(data)


def indexes(data):
    return struct.unpack_from('<ii', data, 0x600)


def row(identifier, parent=None, dependency=None):
    return dict(AbstractPartTypeID=identifier, ParentAbstractPartTypeID=parent,
                DependsOn=dependency, PartPaired=None, BlockFamilyCompatibility=None,
                GarageCategory=None, ModifiedRule=None, RepairCostModifier=None,
                ScrapValueModifier=None, EAPT=None, EUT=None, PartFilename=None,
                SchematicPicname1=None, SchematicPicname2=None)


class PartTypeCacheTests(unittest.TestCase):
    def test_first_matching_duplicate_and_forward_references(self):
        source = (record(0), record(10, 20, 20), record(20), record(20))
        resolved = resolve_part_type_cache(source)
        self.assertEqual(indexes(resolved[1]), (2, 2))
        self.assertEqual(indexes(resolved[2]), (0, 0))

    def test_missing_references_retain_previous_indexes_and_zero_clears(self):
        source = (record(0), record(10, 99, -99, 42, -123), record(20, 0, 0, 77, 88))
        resolved = resolve_part_type_cache(source)
        self.assertEqual(indexes(resolved[1]), (42, -123))
        self.assertEqual(indexes(resolved[2]), (0, 0))

    def test_sentinel_and_unrelated_bytes_are_unchanged_without_mutation(self):
        source = [record(0), record(10, 20), record(20)]
        original = tuple(source)
        resolved = resolve_part_type_cache(source)
        self.assertIsInstance(resolved, tuple)
        self.assertIs(resolved[0], source[0])
        self.assertEqual(tuple(source), original)
        for before, after in zip(source[1:], resolved[1:]):
            self.assertEqual(before[:0x600], after[:0x600])
            self.assertEqual(before[0x608:], after[0x608:])

    def test_builder_marker_order_resolution_and_initial_missing_index(self):
        rows = [row(30, 10, 99), row(10), row(20, 30, 10)]
        built = build_part_type_cache(iter(rows), text_encoding='cp1252')
        marker = bytearray(1596)
        text = b'==No Parent Marker==\0'
        marker[0x347:0x347 + len(text)] = text
        self.assertEqual(built[0], bytes(marker))
        self.assertEqual(tuple(struct.unpack_from('<i', value)[0] for value in built),
                         (0, 30, 10, 20))
        self.assertEqual(tuple(indexes(value) for value in built),
                         ((0, 0), (2, -1), (0, 0), (1, 2)))

    def test_builder_empty_rows_and_cyclic_references_are_preserved(self):
        self.assertEqual(len(build_part_type_cache([], text_encoding='ascii')), 1)
        built = build_part_type_cache([row(10, 20), row(20, 10)], text_encoding='ascii')
        self.assertEqual(tuple(indexes(value)[0] for value in built), (0, 2, 1))

    def test_invalid_cache_shape_and_builder_inputs_rejected(self):
        for records in (None, [], [b'x'], [bytearray(1596)], [record(1)]):
            with self.subTest(records=type(records)):
                with self.assertRaises(ValueError):
                    resolve_part_type_cache(records)
        for rows in (None, 'rows', b'rows', row(1), [1]):
            with self.subTest(rows=type(rows)):
                with self.assertRaises(ValueError):
                    build_part_type_cache(rows, text_encoding='ascii')
        with self.assertRaises(ValueError):
            build_part_type_cache([], text_encoding=None)


if __name__ == '__main__':
    unittest.main()
