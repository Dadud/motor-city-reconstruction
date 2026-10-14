import struct
import unittest
from client.owned_descriptions import apply_owned_descriptions


def record(abstract, branded=0, parent=0, attachment=0, model=b'Model', category=b'Category', description=b'Old'):
    slot = bytearray(1596)
    for offset, value in ((0, abstract), (0x1e3, branded), (0x600, parent), (0x61c, attachment)):
        struct.pack_into('<i', slot, offset, value)
    for offset, text in ((0x20, description), (0x287, model), (0x180, category)):
        slot[offset:offset + len(text) + 1] = text + b'\0'
    return bytes(slot)


def description(slot):
    return slot[0x20:0x180].split(b'\0', 1)[0]


class OwnedDescriptionsTests(unittest.TestCase):
    def test_template_first_match_empty_space_and_missing_preserved(self):
        cache = (record(0), record(55, description=b''), record(55, description=b'Later'))
        source = (record(55), record(99))
        result = apply_owned_descriptions(source, cache, attachment_labels={})
        self.assertEqual(description(result[0]), b' ')
        self.assertEqual(result[1], source[1])
        self.assertEqual(description(source[0]), b'Old')

    def test_branded_assembly_uses_direct_branded_children_in_input_order(self):
        source = (record(101, 1), record(1001, 1, attachment=10),
                  record(2001, 1, attachment=0), record(3001, 0),
                  record(4001, 1, parent=1), record(5001, 1, attachment=99))
        result = apply_owned_descriptions(source, (record(0),), attachment_labels={10: b'Front'})
        self.assertEqual(description(result[0]), b'Model Front Category\nModel Category\nModel  Category')

    def test_whole_line_limit_and_exact_boundary(self):
        for size, expected_count in ((116, 3), (117, 2)):
            # Each line is model(63) + space + category(size-64).
            child = record(1001, 1, model=b'M' * 63, category=b'C' * (size - 64))
            source = (record(101, 1), child, child, child, child)
            output = apply_owned_descriptions(source, (record(0),), attachment_labels={})
            self.assertEqual(len(description(output[0]).split(b'\n')), expected_count)

    def test_leaf_dispatch_is_explicit_and_sequential(self):
        slots = (record(55, 1), record(101, 1))
        with self.assertRaisesRegex(ValueError, 'explicit renderer'):
            apply_owned_descriptions(slots, (record(0),), attachment_labels={})
        seen = []
        output = apply_owned_descriptions(slots, (record(0),), attachment_labels={},
            leaf_description=lambda slot: seen.append(slot) or slot)
        self.assertEqual(seen, [slots[0]])
        self.assertEqual(output[0], slots[0])
        self.assertEqual(description(output[1]), b'')

    def test_exact_351_byte_description_is_retained(self):
        first = record(1001, 1, model=b'M' * 63, category=b'C' * 53)
        other = record(1001, 1, model=b'M' * 63, category=b'C' * 52)
        output = apply_owned_descriptions((record(101, 1), first, other, other, other),
                                          (record(0),), attachment_labels={})
        self.assertEqual(len(description(output[0])), 351)

    def test_missing_known_localization_is_not_silently_empty(self):
        with self.assertRaisesRegex(ValueError, 'attachment label'):
            apply_owned_descriptions((record(101, 1), record(1001, 1, attachment=10)),
                                     (record(0),), attachment_labels={})

    def test_description_pass_inside_postload_sequence(self):
        from client.owned_postload import postprocess_owned_slots
        slots = (record(101, 1), record(1001, 1))
        templates = (record(0), record(101), record(1001, parent=1))
        result = postprocess_owned_slots(slots, templates, finalize_enabled=False,
            description_pass=lambda linked: apply_owned_descriptions(linked, templates, attachment_labels={}))
        self.assertEqual(description(result[0]), b'Model Category')
        self.assertEqual(description(result[1]), b'')
        self.assertEqual(struct.unpack_from('<i', result[1], 0x600)[0], 0)

    def test_invalid_labels_text_and_callback_records(self):
        for labels in ({0: b'Zero'}, {1: b'X\0'}, {1: b'X' * 129}, {True: b'X'}):
            with self.assertRaises(ValueError):
                apply_owned_descriptions((), (record(0),), attachment_labels=labels)
        with self.assertRaises(ValueError):
            apply_owned_descriptions((record(55, 1),), (record(0),), attachment_labels={}, leaf_description=lambda s: b'')
        broken = bytearray(record(55))
        broken[0x20:0x180] = b'X' * 352
        with self.assertRaises(ValueError):
            apply_owned_descriptions((record(55),), (record(0), bytes(broken)), attachment_labels={})


if __name__ == '__main__':
    unittest.main()
