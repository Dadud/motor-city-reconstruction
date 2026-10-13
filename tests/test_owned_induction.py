import struct
import unittest

from client.owned_induction import prune_owned_induction_placeholders


def slot(abstract, owned_id=0, marker=1):
    data = bytearray([marker] * 1596)
    struct.pack_into('<i', data, 0, abstract)
    struct.pack_into('<I', data, 0x5f8, owned_id)
    return bytes(data)


def ids(slots):
    return tuple(struct.unpack_from('<i', value)[0] for value in slots)


class OwnedInductionTests(unittest.TestCase):
    def test_four_ownership_cases_for_each_original_pair(self):
        for first, second, third in ((340001, 340333, 340666),
                                      (350001, 360001, 350666)):
            for own_first, own_second, expected in (
                    (False, False, (third,)), (True, False, (first,)),
                    (False, True, (second,)), (True, True, (first, second))):
                with self.subTest(first=first, ownership=(own_first, own_second)):
                    source = (slot(first, int(own_first)), slot(second, int(own_second)),
                              slot(third))
                    self.assertEqual(ids(prune_owned_induction_placeholders(source)), expected)

    def test_removal_swaps_whole_last_record_before_next_removal(self):
        first, second, third = slot(340001), slot(340333), slot(340666)
        unrelated_one, unrelated_two = slot(99, marker=44), slot(100, marker=55)
        source = (first, unrelated_one, second, third, unrelated_two)
        result = prune_owned_induction_placeholders(source)
        self.assertEqual(result, (unrelated_two, unrelated_one, third))

    def test_duplicate_removal_is_first_only_and_owned_detection_scans_all(self):
        first_a, first_b = slot(340001, marker=11), slot(340333, marker=22)
        second_a, second_b = slot(340001, marker=33), slot(340333, marker=44)
        third = slot(340666, marker=55)
        source = (first_a, second_a, first_b, second_b, third)
        self.assertEqual(prune_owned_induction_placeholders(source),
                         (third, second_a, second_b))
        # A later owned A keeps both A records; the first B still gets removed.
        owned_a = slot(340001, owned_id=99, marker=66)
        result = prune_owned_induction_placeholders((first_a, first_b, third, owned_a))
        self.assertEqual(result, (first_a, owned_a))

    def test_owned_both_removes_only_first_third(self):
        source = (slot(340001, 1), slot(340333, 2), slot(340666, marker=33),
                  slot(340666, marker=44))
        self.assertEqual(prune_owned_induction_placeholders(source),
                         (source[0], source[1], source[3]))

    def test_second_pair_uses_reordered_first_pair_output(self):
        source = (slot(340001), slot(340333), slot(340666), slot(350001),
                  slot(360001), slot(350666), slot(101, marker=77))
        result = prune_owned_induction_placeholders(source)
        self.assertEqual(result, (source[6], source[5], source[2]))

    def test_missing_records_empty_input_and_input_immutability(self):
        self.assertEqual(prune_owned_induction_placeholders([]), ())
        unrelated = slot(77, 0xffffffff, marker=22)
        source = [unrelated, slot(340001, 1)]
        original = tuple(source)
        self.assertEqual(prune_owned_induction_placeholders(source), original)
        self.assertEqual(tuple(source), original)

    def test_invalid_input_records_rejected(self):
        for source in (None, b'bytes', [b'x'], [bytearray(1596)], [1]):
            with self.subTest(source=type(source)):
                with self.assertRaises(ValueError):
                    prune_owned_induction_placeholders(source)


if __name__ == '__main__':
    unittest.main()
