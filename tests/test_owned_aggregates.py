import struct
import unittest

from client.owned_aggregates import (
    apply_owned_component_counts, apply_owned_repair_scrap_aggregates, apply_owned_total_price)


def slot(abstract=55, parent=-1, brand=1, field_c=0, parent_id=0, repair=0, scrap=0, price=0):
    data = bytearray(1596)
    for offset, value in ((0, abstract), (0x600, parent)):
        struct.pack_into('<i', data, offset, value)
    for offset, value in ((0x1e3, brand), (0xc, field_c), (0x60c, parent_id),
                          (0x62c, repair), (0x630, scrap), (0x1eb, price)):
        struct.pack_into('<I', data, offset, value)
    return bytes(data)


def field(record, offset):
    return struct.unpack_from('<I', record, offset)[0]


class OwnedAggregateTests(unittest.TestCase):
    def test_counts_brand_traversal_gate_self_field_and_self_parent_exclusion(self):
        source = (slot(field_c=1), slot(parent=0), slot(parent=0, brand=0),
                  slot(parent=2), slot(parent=0, field_c=9), slot(parent=4))
        result = apply_owned_component_counts(source)
        self.assertEqual(tuple(field(value, 0x638) for value in result), (2, 1, 1, 1, 1, 1))
        self.assertEqual(field(apply_owned_component_counts((slot(parent=0),))[0], 0x638), 1)

    def test_count_reachable_cycles_rejected_but_unbranded_cycle_not_traversed(self):
        with self.assertRaises(ValueError):
            apply_owned_component_counts((slot(parent=1), slot(parent=0)))
        result = apply_owned_component_counts((slot(parent=1, brand=0), slot(parent=0, brand=0)))
        self.assertEqual(tuple(field(value, 0x638) for value in result), (0, 0))

    def test_cost_existing_totals_and_repeated_outer_visits_are_preserved(self):
        source = (slot(101, repair=1, scrap=10), slot(1001, parent=0, repair=2, scrap=20),
                  slot(55, parent=1, repair=3, scrap=30))
        result = apply_owned_repair_scrap_aggregates(source)
        self.assertEqual(tuple(field(value, 0x62c) for value in result), (6, 8, 3))
        self.assertEqual(tuple(field(value, 0x630) for value in result), (60, 80, 30))
        repeated = apply_owned_repair_scrap_aggregates(result)
        self.assertEqual(tuple(field(value, 0x62c) for value in repeated), (17, 14, 3))

    def test_cost_recursive_children_ignore_parent_id_outer_gate(self):
        source = (slot(101, repair=1), slot(1001, parent=0, parent_id=99, repair=2),
                  slot(55, parent=1, repair=3))
        result = apply_owned_repair_scrap_aggregates(source)
        self.assertEqual(tuple(field(value, 0x62c) for value in result), (6, 5, 3))

    def test_cost_wrap_and_non_special_stop_and_unreachable_cycle(self):
        source = (slot(101, repair=0xffffffff, scrap=0xfffffffe),
                  slot(55, parent=0, repair=2, scrap=3), slot(101, parent=1, repair=7, parent_id=1))
        result = apply_owned_repair_scrap_aggregates(source)
        self.assertEqual((field(result[0], 0x62c), field(result[0], 0x630)), (1, 1))
        source = (slot(101, parent=1, parent_id=1), slot(1001, parent=0, parent_id=1))
        self.assertEqual(apply_owned_repair_scrap_aggregates(source), source)
        with self.assertRaises(ValueError):
            apply_owned_repair_scrap_aggregates((slot(101, parent=1), slot(1001, parent=0)))

    def test_total_price_unsigned_wrapping_only_first_field_changes(self):
        source = (slot(price=0xffffffff), slot(price=2), slot(price=0x80000000))
        result = apply_owned_total_price(source)
        self.assertEqual(field(result[0], 0x1eb), 0x80000001)
        self.assertEqual(result[1:], source[1:])
        self.assertEqual(result[0][:0x1eb], source[0][:0x1eb])
        self.assertEqual(result[0][0x1ef:], source[0][0x1ef:])

    def test_outside_parent_values_empty_inputs_and_input_immutability(self):
        source = [slot(parent=-1), slot(parent=999)]
        before = tuple(source)
        for function in (apply_owned_component_counts, apply_owned_repair_scrap_aggregates,
                         apply_owned_total_price):
            self.assertEqual(function([]), ())
            result = function(source)
            self.assertEqual(tuple(source), before)
            self.assertEqual(tuple(struct.unpack_from('<i', value, 0x600)[0] for value in result), (-1, 999))

    def test_deep_counts_use_iterative_traversal(self):
        source = tuple(slot(parent=index - 1) for index in range(1100))
        result = apply_owned_component_counts(source)
        self.assertEqual(field(result[0], 0x638), 1100)
        self.assertEqual(field(result[-1], 0x638), 1)

    def test_deep_cost_chain_uses_iterative_traversal(self):
        source = tuple(slot(1001, parent=index - 1, parent_id=int(index != 0), repair=1)
                       for index in range(1100))
        result = apply_owned_repair_scrap_aggregates(source)
        self.assertEqual(field(result[0], 0x62c), 1100)
        self.assertEqual(field(result[-1], 0x62c), 1)

    def test_invalid_shapes_and_record_limit(self):
        for function in (apply_owned_component_counts, apply_owned_repair_scrap_aggregates,
                         apply_owned_total_price):
            for source in (None, b'bytes', [b'x'], [bytearray(1596)], [bytes(1596)] * 10001):
                with self.subTest(function=function.__name__, source=type(source)):
                    with self.assertRaises(ValueError):
                        function(source)


if __name__ == '__main__':
    unittest.main()
