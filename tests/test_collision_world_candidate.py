import struct
import unittest

from client.body_constructor import construct_body
from client.collision_world_candidate import (CollisionWorldSample,
                                              allocate_trigger_slot,
                                              classify_world_contact,
                                              decode_collision_world_sample,
                                              update_world_contact,
                                              world_sample_overlaps_body)


def record(position=(0, 0, 0), vertical=0, kind=0):
    data = bytearray(0x14)
    struct.pack_into('<3i', data, 0, *position)
    struct.pack_into('<h', data, 0x0c, vertical)
    data[0x13] = kind
    return data


class CollisionWorldSampleTests(unittest.TestCase):
    def setUp(self):
        self.body = bytearray(construct_body(bytearray(0x2000), 0x1000, 1.,
                                             (1., 1., 1.), 0, 0))

    @staticmethod
    def contact_record(kind, sample_id=7):
        data = bytearray(0x14)
        struct.pack_into('<H', data, 0x0e, sample_id)
        data[0x13] = kind
        return data

    def test_all_packed_kinds_select_their_scale_and_radius(self):
        expected = ((0, 1., 3.), (1, .5, 12.),
                    (2, 2., 2.), (3, 1., 1.))
        for kind, vertical_scale, radius in expected:
            with self.subTest(kind=kind):
                value = decode_collision_world_sample(record(vertical=1024, kind=kind))
                self.assertEqual(value.kind, kind)
                self.assertAlmostEqual(value.vertical_value, vertical_scale * 4.)
                self.assertEqual(value.radius, radius)

    def test_coordinates_are_signed_16_16_values(self):
        value = decode_collision_world_sample(
            record((65536, -32768, -2147483648), kind=0))
        self.assertEqual(value.position, (1., -.5, -32768.))

    def test_kind_two_vertical_scaling_wraps_like_a_signed_word(self):
        value = decode_collision_world_sample(record(vertical=22499, kind=2))
        self.assertAlmostEqual(value.vertical_value, -80.2265625)

    def test_record_must_cover_the_complete_packed_sample(self):
        with self.assertRaises(ValueError):
            decode_collision_world_sample(bytes(0x13))

    def test_world_candidate_passes_radius_and_oriented_extent_gates(self):
        sample = CollisionWorldSample((0., 0., 0.), 1., 3., 0)
        self.assertTrue(world_sample_overlaps_body(self.body, sample))
        self.assertFalse(world_sample_overlaps_body(
            self.body, CollisionWorldSample((4., 0., 0.), 3., 3., 0)))

    def test_world_candidate_uses_strict_bounds(self):
        self.assertFalse(world_sample_overlaps_body(
            self.body, CollisionWorldSample((0., 0., 0.), 10., 0., 0)))
        self.assertFalse(world_sample_overlaps_body(
            self.body, CollisionWorldSample((4., 0., 0.), 3., 3., 0)))

    def test_classifier_maps_simple_contact_kinds(self):
        self.assertEqual(classify_world_contact(
            self.body, self.contact_record(1), 0).decision, 1)
        self.assertEqual(classify_world_contact(
            self.body, self.contact_record(1), 0).type_code, 0x1d)
        self.assertEqual(classify_world_contact(
            self.body, self.contact_record(3), 0).decision, 2)
        self.assertEqual(classify_world_contact(
            self.body, self.contact_record(3), 0).type_code, 0x1a)

    def test_classifier_uses_signed_trigger_state_and_speed_gate_tiers(self):
        record = self.contact_record(2)
        self.assertEqual(classify_world_contact(self.body, record, 0).decision, 0)
        for speed, tier in ((18000., None), (18750., 2), (40000., 3)):
            struct.pack_into('<f', self.body, 0x3c0, speed)
            result = classify_world_contact(self.body, record, 0xff)
            self.assertEqual(result.trigger_tier, tier)
            self.assertEqual(result.decision, 1 if tier is None else -1)
            if tier is not None:
                self.assertEqual(result.trigger_state_after, 0xfe)

    def test_classifier_has_zero_trigger_threshold_for_runtime_owned_state(self):
        self.body[6] = 1
        self.body[0x474] = 2
        struct.pack_into('<f', self.body, 0x3c0, 0.)
        result = classify_world_contact(self.body, self.contact_record(2), -1)
        self.assertEqual((result.decision, result.trigger_tier), (-1, 3))

    def test_classifier_computes_heading_for_successful_slot(self):
        self.body[6] = 1
        self.body[0x474] = 2
        struct.pack_into('<f', self.body, 0x14, 1.)
        struct.pack_into('<f', self.body, 0x1c, 0.)
        result = classify_world_contact(self.body, self.contact_record(2), -1,
                                        allocation_result=5)
        self.assertEqual((result.decision, result.trigger_tier), (-1, 3))
        self.assertEqual((result.trigger_state_after, result.trigger_angle_after,
                          result.trigger_substate_after), (5, 0x40, 0))

    def test_trigger_slot_allocation_initializes_only_the_free_record_fields(self):
        slots = bytearray(0x1800)
        slots[8:0x18] = bytes(range(1, 17))
        resources = [0] * 256
        resources[2] = 0x12345678
        result = allocate_trigger_slot(slots, resources, 2, 0x87654321)
        self.assertEqual(result.result, 0)
        self.assertEqual(struct.unpack_from('<II', result.slots, 0),
                         (0x12345678, 0x87654321))
        self.assertEqual(struct.unpack_from('<III', result.slots, 0x0c), (2, 1, 0))
        self.assertEqual(result.slots[8:0x0c], bytes(range(1, 5)))

    def test_trigger_slot_failure_sentinels_preserve_the_slot_table(self):
        resources = [1] * 256
        empty = bytes(0x1800)
        self.assertEqual(allocate_trigger_slot(empty, resources, 256, 1).result, 0xff)
        full = bytearray(empty)
        for index in range(256):
            struct.pack_into('<I', full, index * 0x18, index + 1)
        result = allocate_trigger_slot(full, resources, 2, 1)
        self.assertEqual(result.result, 0x1ff)
        self.assertEqual(result.slots, bytes(full))
        resources[2] = 0
        self.assertEqual(allocate_trigger_slot(empty, resources, 2, 1).slots, empty)

    def test_world_contact_composes_resource_allocation_and_angle_write(self):
        self.body[6] = 1
        self.body[0x474] = 2
        struct.pack_into('<f', self.body, 0x14, 1.)
        resources = [0] * 256
        resources[3] = 0x12345678
        result = update_world_contact(
            self.body, self.contact_record(2), b'\xff\x11\x22',
            bytes(0x1800), resources, 0x87654321)
        self.assertEqual(result.sample_state, b'\x00\x40\x00')
        self.assertEqual(struct.unpack_from('<III', result.trigger_slots, 0x0c),
                         (2, 0, 0x40))
        self.assertEqual(struct.unpack_from('<II', result.trigger_slots, 0),
                         (0x12345678, 0x87654321))

    def test_missing_resource_sets_failure_sentinel_and_preserves_state_tail(self):
        self.body[6] = 1
        self.body[0x474] = 2
        resources = [0] * 256
        result = update_world_contact(
            self.body, self.contact_record(2), b'\xff\x33\x44',
            bytes(0x1800), resources, 0x87654321)
        self.assertEqual(result.sample_state, b'\xfe\x33\x44')
        self.assertEqual(result.trigger_slots, bytes(0x1800))

    def test_signed_slot_index_boundary_retains_allocator_initialization(self):
        self.body[6] = 1
        self.body[0x474] = 2
        resources = [0] * 256
        resources[3] = 0x12345678
        slots = bytearray(0x1800)
        for index in range(128):
            struct.pack_into('<I', slots, index * 0x18, index + 1)
        result = update_world_contact(
            self.body, self.contact_record(2), b'\xff\x00\x00',
            slots, resources, 0x87654321)
        self.assertEqual(result.sample_state, b'\xfe\x00\x00')
        self.assertEqual(struct.unpack_from('<III', result.trigger_slots,
                                            128 * 0x18 + 0x0c), (2, 1, 0))


if __name__ == '__main__':
    unittest.main()
