import struct
import unittest

from client.world_object_reset import (OWNER_SIZE, WheelResetCache,
                                       reset_wheel_records,
                                       reset_world_object,
                                       reset_world_object_drive_state,
                                       reset_world_object_geometry,
                                       reset_world_object_prefix,
                                       drive_reset_state_result,
                                       WorldObjectResetServices)
from client.world_object_path_reset import PathResetGlobals
from client.travel_map import TravelMapCache


class WorldObjectResetTests(unittest.TestCase):
    def test_drive_reset_state_forced_flags_and_owner_selector(self):
        record = bytearray(OWNER_SIZE)
        for flag in (0x200, 0x2, 0x10):
            struct.pack_into('<I', record, 0x474, flag)
            self.assertEqual(drive_reset_state_result(
                record, owner_address=0x1000, selected_owner=0x2000,
                result_mask=0xA5), 1)
        struct.pack_into('<I', record, 0x474, 0)
        self.assertEqual(drive_reset_state_result(
            record, owner_address=0x1000, selected_owner=0x1000,
            result_mask=0xA5), 0xA5)
        self.assertEqual(drive_reset_state_result(
            record, owner_address=0x1000, selected_owner=0x2000,
            result_mask=0xA5), 0)

    def test_public_reset_composes_verified_stages_through_path_child(self):
        record = bytearray(b'\xa5' * OWNER_SIZE)
        struct.pack_into('<i', record, 0x364, 5)
        struct.pack_into('<i', record, 0x370, 6)
        struct.pack_into('<i', record, 0x464, 99)
        struct.pack_into('<i', record, 0x47c, 0)
        struct.pack_into('<i', record, 0x480, 0)
        struct.pack_into('<I', record, 0xac0, 1)
        struct.pack_into('<I', record, 0xae4, 1)
        profile = bytearray(0x690)
        struct.pack_into('<I', profile, 0x68c, 1)
        struct.pack_into('<f', profile, 0x374, 1.0)
        track_rows = bytearray(60 * 0x1c)
        track_rows[7 * 0x1c + 0x18] = 80
        struct.pack_into('<i', record, 0x5ac, 2)
        for offset in (0x1810, 0x1814, 0x1818, 0x181c):
            struct.pack_into('<f', record, offset, 1.0)
        cache = WheelResetCache(False, 0.0)
        calls = []
        services = WorldObjectResetServices(
            shared_reset_value=0x12345678,
            profile=profile,
            path_globals=PathResetGlobals(60, 10, 30, 0, 4, 99, 1),
            shared_reset_generation=0x87654321,
            shared_reset_metadata=0x11223344,
            primary_path_count=60,
            fallback_path_count=60,
            path_origin=10,
            secondary_path_origin=30,
            wrapped_path_mode=0,
            reverse_path_mode=0,
            reset_motion_value=0x55667788,
            track_rows=bytes(track_rows),
            default_track_attribute=0,
            track_rate_count=4,
            designated_mode=99,
            mouse_controller_enabled=0,
            mouse_controller_initialized=0,
            mouse_input_mode=3,
            mouse_environment_mode=0,
            mouse_position_x=0,
            mouse_position_y=0,
            set_mouse_state=lambda _selector, _value: True,
            virtual_reset_gate=lambda selector, owner: int(
                selector == 0x0f and owner is record),
            reset_drive_state=lambda _: 0,
            reset_component=lambda image: reset_wheel_records(
                image, cache=cache, profile_scale=8.0),
            path_interface_query=lambda selector, _: 0 if selector == 0x16 else 1,
            advance_path_state=lambda _: calls.append(('advance',)),
            travel_map_cache=TravelMapCache(bytearray(4)),
            allocate_travel_map=lambda _resource, size, _flags: bytearray(size),
            designated_mode_action=lambda: calls.append(('designated',)),
            complete_interface_reset=lambda *args: calls.append(('interface', args)),
        )

        result = reset_world_object(record, services=services)

        self.assertIs(result, record)
        self.assertTrue(cache.initialized)
        self.assertEqual(struct.unpack_from('<i', record, 0x364)[0], 6)
        self.assertEqual(struct.unpack_from('<I', record, 0x410)[0], 0x55667788)
        self.assertAlmostEqual(struct.unpack_from('<f', record, 0xa44)[0],
                               17.8812 * (0.75 + 0.25 / 3), places=5)
        self.assertEqual(record[0xa69], 3)
        self.assertEqual(struct.unpack_from('<i', record, 0xab4)[0], 14)
        self.assertEqual(calls, [('designated',), ('interface', (1, record))])

    def test_prefix_masks_flags_and_preserves_unowned_bytes(self):
        record = bytearray(b'\xa5' * OWNER_SIZE)
        struct.pack_into('<I', record, 0xdf4, 0xffffffff)
        struct.pack_into('<I', record, 0xe14, 0xffffffff)
        record[0x474] = 0x10
        record[0xe50] = 0x7b
        untouched = (bytes(record[:0x38]), bytes(record[0x418:0x474]),
                     bytes(record[0x500:0xa30]),
                     bytes(record[0x1234:]))

        reset_world_object_prefix(record, 0x12345678)

        self.assertEqual(struct.unpack_from('<3I', record, 0x38), (0, 0, 0))
        self.assertEqual(struct.unpack_from('<3I', record, 0xbe8),
                         (0x47c35000,) * 3)
        self.assertEqual(struct.unpack_from('<II', record, 0x410),
                         (0x12345678, 0x12345678))
        self.assertEqual(struct.unpack_from('<I', record, 0xdf4)[0], 0xfffffeff)
        self.assertEqual(struct.unpack_from('<I', record, 0xe14)[0], 0xffffff3f)
        self.assertEqual(record[0xe50], 0x7b)
        self.assertEqual((bytes(record[:0x38]), bytes(record[0x418:0x474]),
                          bytes(record[0x500:0xa30]),
                          bytes(record[0x1234:])), untouched)

    def test_reset_value_must_be_uint32(self):
        with self.assertRaises(ValueError):
            reset_world_object_prefix(bytearray(OWNER_SIZE), -1)

    def test_geometry_reset_copies_matrices_and_orders_children(self):
        record = bytearray(b'\xa5' * OWNER_SIZE)
        first = tuple(range(9))
        second = tuple(range(9, 18))
        struct.pack_into('<9I', record, 0x78, *first)
        struct.pack_into('<9I', record, 0x9c, *second)
        struct.pack_into('<I', record, 0x478, 0xffffffff)
        calls = []

        reset_world_object_geometry(record,
            reset_component=lambda image: calls.append(('component', image is record)),
            update_attachment=lambda image: calls.append(('attachment', image is record)))

        self.assertEqual(struct.unpack_from('<9I', record, 0xc10), first)
        self.assertEqual(struct.unpack_from('<9I', record, 0xc34), second)
        self.assertEqual(struct.unpack_from('<I', record, 0xc0c)[0], 0x3f800000)
        self.assertEqual(struct.unpack_from('<I', record, 0x478)[0], 0xfffff7ff)
        self.assertEqual(calls, [('component', True), ('attachment', True)])

    def test_wheel_records_use_lazy_shared_factor_and_copy_source_state(self):
        record = bytearray(b'\xa5' * OWNER_SIZE)
        query = bytes(range(0x44))
        record[0x370:0x370 + 0x44] = query
        struct.pack_into('<I', record, 0x404, 7)
        struct.pack_into('<I', record, 0x18ec, 0x11112222)
        struct.pack_into('<I', record, 0x18f0, 0x33334444)
        cache = WheelResetCache(False, 0.0)

        reset_wheel_records(record, cache=cache, profile_scale=8.0)

        self.assertTrue(cache.initialized)
        self.assertEqual(cache.factor, 2.0)
        for index in range(4):
            base = 0x600 + index * 0x10c
            self.assertEqual(record[base + 0x10:base + 0x54], query)
            self.assertEqual(struct.unpack_from('<I', record, base + 0x54)[0], 7)
            self.assertEqual(struct.unpack_from('<f', record, base + 0xd0)[0], 2.0)
            source = 0x11112222 if index < 2 else 0x33334444
            self.assertEqual(struct.unpack_from('<I', record, base + 0xb8)[0], source)

    def test_drive_reset_zero_virtual_result_takes_early_return(self):
        record = bytearray(OWNER_SIZE)
        profile = bytearray(0x690)
        struct.pack_into('<I', record, 0xac0, 1)
        struct.pack_into('<I', profile, 0x68c, 1)
        struct.pack_into('<f', profile, 0x374, 1.0)
        reset_world_object_drive_state(record, profile,
            reset_drive_state=lambda _: self.fail('disabled profile called 0x43b570'),
            interface_result=0)
        self.assertEqual(struct.unpack_from('<I', record, 0xb54)[0], 1)
        self.assertEqual(record[0xa62], 2)
        self.assertEqual(struct.unpack_from('<I', record, 0xae4)[0] & 1, 1)
        self.assertAlmostEqual(struct.unpack_from('<f', record, 0xad4)[0], 0.3)
        self.assertEqual(struct.unpack_from('<f', record, 0xadc)[0], 20.0)
        self.assertEqual(struct.unpack_from('<f', record, 0xacc)[0], 20.0)


if __name__ == '__main__':
    unittest.main()
