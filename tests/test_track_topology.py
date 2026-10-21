import unittest

from client.track_topology import (path_index_is_forward, step_path_index,
                                   track_index_is_rejected,
                                   bounded_path_index, collision_search_bit,
                                   collision_search_slot,
                                   reset_track_attribute, reset_path_index)
from client.collision_recovery import search_surface_correction


class TrackTopologyTests(unittest.TestCase):
    def test_reset_path_mapping_keeps_c_signed_remainder(self):
        self.assertEqual(reset_path_index(
            51, -13, primary_count=12, fallback_count=8,
            primary_origin=0, secondary_origin=0,
            wrapped_mode=0, reverse_mode=0), -141)
        self.assertEqual(reset_path_index(
            5, 3, primary_count=0, fallback_count=20,
            primary_origin=8, secondary_origin=2,
            wrapped_mode=1, reverse_mode=0), 63)

    def test_reset_track_attribute_reads_selected_row_byte(self):
        table = bytearray(3 * 0x1c)
        table[0x18:0x1a] = b'\x12\x34'
        table[2 * 0x1c + 0x18:2 * 0x1c + 0x1a] = b'\xab\xcd'
        self.assertEqual(reset_track_attribute(table, 0, 0, default_value=0), 0x12)
        self.assertEqual(reset_track_attribute(table, 0, 5, default_value=0), 0x34)
        self.assertEqual(reset_track_attribute(table, 2, 1, default_value=0), 0xcd)
        self.assertEqual(reset_track_attribute(None, 2, 0, default_value=0x77), 0x77)

    def test_wrapped_ordering_selects_short_route_at_track_boundary(self):
        self.assertFalse(path_index_is_forward(12, 1, 10, wrapped_ordering=False))
        self.assertTrue(path_index_is_forward(12, 1, 10, wrapped_ordering=True))

    def test_single_wrap_preserves_native_one_adjustment_behavior(self):
        self.assertEqual(step_path_index(11, 1, 12), 0)
        self.assertEqual(step_path_index(0, -1, 12), 11)
        self.assertEqual(step_path_index(0, -25, 12), -13)

    def test_clamped_mode_uses_explicit_validity_predicate(self):
        self.assertEqual(step_path_index(4, 9, 12, wrap_mode=False,
                                         index_is_rejected=lambda i: i != 11), 11)
        self.assertEqual(step_path_index(4, -9, 12, wrap_mode=False,
                                         index_is_rejected=lambda _: True), 4)

    def test_clamped_mode_requires_validity_predicate(self):
        with self.assertRaises(ValueError):
            step_path_index(0, 1, 12, wrap_mode=False)

    def test_index_rejection_uses_native_limit_bounds(self):
        self.assertFalse(track_index_is_rejected(
            5, range_start=2, range_end=10, lower_limit=1, upper_limit=12))
        self.assertTrue(track_index_is_rejected(
            13, range_start=2, range_end=10, lower_limit=1, upper_limit=12))

    def test_alternate_path_step_clamps_without_repeated_wrapping(self):
        self.assertEqual(bounded_path_index(3, -5, 10, clamp=True), 0)
        self.assertEqual(bounded_path_index(9, 8, 10, clamp=True), 9)
        self.assertEqual(bounded_path_index(0, -15, 10, clamp=False), -5)

    def test_collision_search_mask_clamps_slot_and_reads_high_bit_first(self):
        self.assertEqual(collision_search_bit(0x8000, -10), 0x8000)
        self.assertEqual(collision_search_bit(0x0001, 14), 1)
        self.assertEqual(collision_search_bit(0xffff, 4), 0x400)

    def test_collision_search_spacing_chooses_signed_path_side(self):
        self.assertEqual(collision_search_slot(4.0, 6.0, 0.0), 7)
        self.assertEqual(collision_search_slot(4.0, 6.0, 3.0), 7)
        self.assertEqual(collision_search_slot(4.0, 6.0, -2.0), 6)
        self.assertEqual(collision_search_slot(4.0, 6.0, 100.0), 13)
        self.assertEqual(collision_search_slot(4.0, 6.0, -100.0), 0)

    def test_surface_recovery_visits_rows_then_falls_back_to_initial_track(self):
        owner = bytearray(0xDF8)
        owner[0x370:0x374] = (0).to_bytes(4, 'little')
        rows = ((2.0, 4.0, 1, 2), (1.0, 3.0, 0, 0))
        probes = []
        result = search_surface_correction(
            owner, 0, path_rows=rows, path_count=2, attempts=2,
            wrapped_ordering=False, wrapped_index=True,
            probe=lambda _owner, index, offset, *_: probes.append((index, offset)) or 0,
            apply_response=lambda *_: self.fail('unexpected collision response'),
            fallback_seed=lambda index, _mode: -7.0 if index == 0 else 99.0)
        self.assertEqual(probes, [
            (0, 2.0), (0, -1.0), (0, 6.0), (0, -3.0), (0, -7.0)])
        self.assertEqual(result, (None, None, 5))

    def test_surface_recovery_requires_full_shared_topology_count(self):
        with self.assertRaises(ValueError):
            search_surface_correction(
                bytearray(0xDF8), 0, path_rows=((1.0, 1.0, 0, 0),),
                path_count=1, attempts=0, wrapped_ordering=False,
                wrapped_index=True, probe=lambda *_: 0,
                apply_response=lambda *_: None, fallback_seed=lambda *_: 0.0)


if __name__ == '__main__':
    unittest.main()
