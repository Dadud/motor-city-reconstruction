import struct
import unittest

from client.owned_insertion import insert_owned_placeholders


def record(abstract, parent=0, owned=0, attachment=0, part_type=0,
           brand=b'Brand', model=b'Model', description=b'Description', category=b'Category'):
    data = bytearray(1596)
    for offset, value in ((0, abstract), (0x600, parent), (0x61c, attachment),
                          (0x1e7, part_type), (0x5f8, owned)):
        struct.pack_into('<i', data, offset, value)
    for offset, text in ((0x2c7, brand), (0x307, model), (0x347, description), (0x180, category)):
        data[offset:offset + len(text) + 1] = text + b'\0'
    return bytes(data)


def integer(slot, offset=0):
    return struct.unpack_from('<i', slot, offset)[0]


def text(slot, offset):
    return slot[offset:].split(b'\0', 1)[0]


class OwnedInsertionTests(unittest.TestCase):
    def test_empty_input_returns_empty_after_cache_validation(self):
        templates = (record(0), record(101))
        self.assertEqual(insert_owned_placeholders([], templates), ())
        self.assertEqual(insert_owned_placeholders((), templates), ())
        with self.assertRaises(ValueError):
            insert_owned_placeholders([], (record(0), record(101, parent=-1)))

    def test_growing_walk_inserts_nested_special_placeholders_in_cache_order(self):
        templates = (record(0), record(101), record(1001, 1), record(50, 2), record(51, 1))
        source = [record(101, owned=1)]
        result = insert_owned_placeholders(source, templates)
        self.assertEqual(tuple(integer(slot) for slot in result), (101, 1001, 51, 50))
        self.assertEqual(integer(result[3], 0x600), 2)  # Still a template-cache index.
        self.assertEqual(source, [record(101, owned=1)])

    def test_only_owned_or_original_special_parents_expand(self):
        templates = (record(0), record(70), record(71, 1), record(101), record(72, 3))
        self.assertEqual(len(insert_owned_placeholders((record(70),), templates)), 1)
        self.assertEqual(len(insert_owned_placeholders((record(70, owned=1),), templates)), 2)
        self.assertEqual(len(insert_owned_placeholders((record(101),), templates)), 2)
        self.assertEqual(len(insert_owned_placeholders((record(0, owned=1),), templates)), 1)
        self.assertEqual(len(insert_owned_placeholders((record(999, owned=1),), templates)), 1)

    def test_all_mapped_attachment_types_have_exact_two_slots(self):
        children = (100001, 110001, 10001, 12001, 11001, 13001, 14001)
        templates = (record(0), record(101)) + tuple(record(identifier, 1) for identifier in children)
        result = insert_owned_placeholders((record(101),), templates)
        self.assertEqual(tuple((integer(slot), integer(slot, 0x61c)) for slot in result[1:]),
                         tuple((identifier, attachment) for identifier in children for attachment in (10, 11)))

    def test_existing_type_and_attachment_suppresses_only_exact_pair(self):
        templates = (record(0), record(101), record(10001, 1), record(55, 1))
        source = (record(101), record(10001, attachment=10), record(55, attachment=9))
        result = insert_owned_placeholders(source, templates)
        self.assertEqual(tuple((integer(slot), integer(slot, 0x61c)) for slot in result[3:]),
                         ((10001, 11), (55, 0)))

    def test_part_type_2001_suppresses_three_children(self):
        templates = (record(0), record(101)) + tuple(record(identifier, 1) for identifier in (23001, 34001, 35001, 55))
        source = (record(101), record(99, part_type=2001))
        result = insert_owned_placeholders(source, templates)
        self.assertEqual(tuple(integer(slot) for slot in result), (101, 99, 55))

    def test_duplicate_uses_first_clone_but_current_child_description(self):
        templates = (record(0), record(101), record(50, parent=0, description=b'First', model=b'First model'),
                     record(50, parent=1, description=b'Current', model=b'Other model'))
        result = insert_owned_placeholders((record(101),), templates)
        self.assertEqual(text(result[1], 0x347), b'Current')
        self.assertEqual(text(result[1], 0x307), b'First model')
        self.assertEqual(integer(result[1], 0x600), 0)

    def test_display_modes_and_category_without_owned_year_format(self):
        templates = (record(0), record(1001), record(101, 1, category=b'Vehicles'))
        result = insert_owned_placeholders((record(1001),), templates)
        self.assertEqual(text(result[1], 0x207), b'Brand Model')
        self.assertEqual(text(result[1], 0x180), b'Vehicles')
        result = insert_owned_placeholders((record(1001),), templates, display_mode=0)
        self.assertEqual(text(result[1], 0x207), b'Model')
        self.assertEqual(text(result[1], 0x287), b'Model')
        templates = (record(0), record(101), record(55, 1))
        self.assertEqual(text(insert_owned_placeholders((record(101),), templates, display_mode=1)[1], 0x207),
                         b'Brand Model')

    def test_only_clone_override_fields_change(self):
        templates = (record(0), record(101), record(55, 1))
        result = insert_owned_placeholders((record(101),), templates)
        expected = bytearray(templates[2])
        expected[0x207:0x207 + 12] = b'Brand Model\0'
        self.assertEqual(result[1], bytes(expected))
        self.assertEqual(result[0], record(101))

    def test_limits_invalid_modes_and_bounded_text(self):
        templates = (record(0), record(101), record(55, 1))
        for kwargs in ({'max_parts': 1}, {'max_parts': 0}, {'max_parts': True},
                       {'display_mode': True}, {'display_mode': -1}, {'display_mode': 2**32}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    insert_owned_placeholders((record(101),), templates, **kwargs)
        for offset in (0x347, 0x307, 0x2c7, 0x180):
            corrupt = bytearray(templates[2])
            corrupt[offset:offset + 64] = b'X' * 64
            with self.subTest(offset=offset):
                with self.assertRaises(ValueError):
                    insert_owned_placeholders((record(101),), templates[:2] + (bytes(corrupt),))


if __name__ == '__main__':
    unittest.main()
