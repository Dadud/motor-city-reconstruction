import struct
import unittest

from client.owned_postload import postprocess_owned_slots


def record(abstract, parent=0, depends=0, owned=1, brand=1, attachment=0,
           repair=0, price=0, count=99):
    data = bytearray(1596)
    for offset, value in ((0, abstract), (0x600, parent), (0x604, depends),
                          (0x61c, attachment)):
        struct.pack_into('<i', data, offset, value)
    for offset, value in ((0x5f8, owned), (0x1e3, brand), (0x62c, repair),
                          (0x1eb, price), (0x638, count), (0x634, 88)):
        struct.pack_into('<I', data, offset, value)
    return bytes(data)


def field(slot, offset):
    return struct.unpack_from('<I', slot, offset)[0]


def identity(slots):
    return slots


class OwnedPostloadTests(unittest.TestCase):
    def test_description_observes_links_flags_and_precedes_numeric_passes(self):
        templates = (record(0), record(101), record(55, parent=1, depends=1))
        source = (record(101, price=10, repair=1), record(55, price=20, repair=2))
        seen = []

        def description(slots):
            self.assertIsInstance(slots, tuple)
            seen.append(slots)
            self.assertEqual(field(slots[1], 0x600), 0)
            self.assertEqual(field(slots[1], 0x604), 0)
            self.assertEqual(tuple(field(slot, 0x634) for slot in slots), (1, 1))
            self.assertEqual(tuple(field(slot, 0x638) for slot in slots), (99, 99))
            self.assertEqual(field(slots[0], 0x62c), 1)
            child = bytearray(slots[1])
            struct.pack_into('<I', child, 0x62c, 5)
            return (slots[0], bytes(child))

        result = postprocess_owned_slots(source, templates, finalize_enabled=False,
                                        description_pass=description)
        self.assertEqual(len(seen), 1)
        self.assertEqual(tuple(field(slot, 0x638) for slot in result), (2, 1))
        self.assertEqual(field(result[0], 0x62c), 6)
        self.assertEqual(field(result[0], 0x1eb), 30)
        self.assertEqual(source[1], record(55, price=20, repair=2))

    def test_dependency_flag_clear_happens_after_all_flag_initialization(self):
        templates = (record(0), record(101), record(20001, parent=1))
        source = (record(101), record(20001))
        observed = []
        result = postprocess_owned_slots(source, templates, finalize_enabled=False,
                                        description_pass=lambda slots: observed.append(slots) or slots)
        self.assertEqual(tuple(field(slot, 0x634) for slot in observed[0]), (1, 0))
        self.assertEqual(field(result[1], 0x634), 0)

    def test_finalize_disabled_and_mode_one_bypass_insertion_and_pruning(self):
        templates = (record(0), record(101), record(55, parent=1),
                     record(340001, parent=1), record(340333, parent=1), record(340666, parent=1))
        source = (record(101), record(340001, owned=0), record(340333, owned=0), record(340666, owned=0))
        for options in ({'finalize_enabled': False}, {'finalize_mode': 1}):
            with self.subTest(options=options):
                result = postprocess_owned_slots(source, templates, enriched=False, reorder=False, **options)
                self.assertEqual(tuple(field(slot, 0) for slot in result), (101, 340001, 340333, 340666))
        result = postprocess_owned_slots(source, templates, enriched=False, reorder=False)
        self.assertEqual(tuple(field(slot, 0) for slot in result), (101, 55, 340666))

    def test_optional_reorder_before_parent_selection_in_unenriched_path(self):
        templates = (record(0), record(101), record(55, parent=1), record(56, parent=1))
        source = (record(101), record(56), record(55))
        reordered = postprocess_owned_slots(source, templates, finalize_enabled=False, enriched=False)
        self.assertEqual(tuple(field(slot, 0) for slot in reordered), (101, 55, 56))
        unchanged = postprocess_owned_slots(source, templates, finalize_enabled=False, enriched=False, reorder=False)
        self.assertEqual(tuple(field(slot, 0) for slot in unchanged), (101, 56, 55))

    def test_unenriched_skips_callback_counts_costs_but_still_sums_price(self):
        templates = (record(0), record(101), record(55, parent=1))
        source = (record(101, price=0xffffffff, repair=1), record(55, price=2, repair=3))

        def forbidden(slots):
            self.fail('unenriched processing called description pass')

        result = postprocess_owned_slots(source, templates, finalize_enabled=False,
                                        enriched=False, description_pass=forbidden)
        self.assertEqual(field(result[0], 0x1eb), 1)
        self.assertEqual(tuple(field(slot, 0x638) for slot in result), (99, 99))
        self.assertEqual(tuple(field(slot, 0x62c) for slot in result), (1, 3))

    def test_callback_missing_or_invalid_output_rejected(self):
        source, templates = (record(101),), (record(0), record(101))
        with self.assertRaisesRegex(ValueError, 'explicit description'):
            postprocess_owned_slots(source, templates)
        for output in (None, (), [b'x'], [bytearray(1596)], [record(101), record(101)]):
            with self.subTest(output=type(output)):
                with self.assertRaises(ValueError):
                    postprocess_owned_slots(source, templates, description_pass=lambda slots: output)

    def test_modes_flags_record_limits_and_unresolved_dependencies(self):
        source, templates = (record(101),), (record(0), record(101))
        for options in ({'finalize_enabled': 1}, {'reorder': 0}, {'enriched': 1},
                        {'finalize_mode': True}, {'finalize_mode': -1},
                        {'display_mode': 2**32}):
            with self.subTest(options=options):
                with self.assertRaises(ValueError):
                    postprocess_owned_slots(source, templates, description_pass=identity, **options)
        for invalid in ([], None, [b'x'], [bytearray(1596)], [record(101)] * 10001):
            with self.assertRaises(ValueError):
                postprocess_owned_slots(invalid, templates, description_pass=identity)
        with self.assertRaises(ValueError):
            postprocess_owned_slots(source, (record(0), record(101, depends=-1)), description_pass=identity)


if __name__ == '__main__':
    unittest.main()
