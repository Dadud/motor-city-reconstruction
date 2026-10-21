import struct
import unittest

from client.track_surface_lookup import TrackSurfaceMemory, TrackSurfaceWorld
from client.world_object_environment import EnvironmentCallbacks, environment_step
from client.track_plane import surface_height
from client.collision_impulse import plane_height
from client.tire_response import f32
from tools.track_surface_cases import BASE, BLOCKS, PATH, fixture


def make_callbacks(mode=0):
    arena, root, query = fixture(mode, 0, 0, 0, 0, 8, 8, 0)
    memory = TrackSurfaceMemory(root + bytes(65536 - len(root)), bytes(arena), BASE)
    world = TrackSurfaceWorld(memory, (0.0, 0.0), (1.0, 1.0),
                              BLOCKS, PATH, 2, 24)
    callbacks = EnvironmentCallbacks(
        world=world, adjust_contact=lambda *_: None,
        reset_vehicle_state=lambda _: None, vertical_step=4.0)
    return callbacks, query


def make_record(query):
    record = bytearray(0x4F8)
    record[4] = 1
    struct.pack_into('<3f', record, 8, 8.0, 2.0, 8.0)
    struct.pack_into('<3f', record, 0x358, 8.0, 2.0, 8.0)
    struct.pack_into('<9f', record, 0x78, 1,0,0, 0,1,0, 0,0,1)
    struct.pack_into('<66f', record, 0xE0, *([0.0] * 66))
    record[0x370:0x370 + 68] = query
    struct.pack_into('<II', record, 0x370, 0, 0)
    struct.pack_into('<I', record, 0x378, 1)
    struct.pack_into('<3f', record, 0x370 + 44, 0.0, 1.0, 0.0)
    return record


class WorldObjectEnvironmentTests(unittest.TestCase):
    def test_contact_clearance_keeps_extended_height_until_final_store(self):
        point = (8.835801124572754, 1.0223900079727173,
                 8.65644645690918)
        normal = (0.003082275390625, 0.999969482421875,
                  -0.006134033203125)
        origin = (0.0, 0.0, 0.0)
        extended_result = f32(point[1] - surface_height(normal, origin, point))
        helper_result_stored_first = f32(point[1] - plane_height(normal, origin, point))
        self.assertEqual(extended_result, 0.9965246319770813)
        self.assertEqual(helper_result_stored_first, 0.9965246915817261)
        self.assertNotEqual(extended_result, helper_result_stored_first)

    def test_inactive_owner_does_not_call_native_children(self):
        calls = []
        callbacks, query = make_callbacks()
        callbacks = EnvironmentCallbacks(
            world=callbacks.world,
            adjust_contact=lambda *args: calls.append(args),
            reset_vehicle_state=lambda *args: calls.append(args),
            vertical_step=callbacks.vertical_step)
        environment_step(make_record(query), callbacks=callbacks,
                         environment_enabled=True)
        self.assertEqual(calls, [])

    def test_live_spatial_query_drives_transform_and_contacts(self):
        callbacks, query = make_callbacks()
        record = make_record(query)
        environment_step(record, callbacks=callbacks, environment_enabled=True)
        self.assertIn(struct.unpack_from('<I', record, 0x36C)[0], (0, 1))
        self.assertEqual(struct.unpack_from('<I', record, 0x354)[0], 1)
        self.assertEqual(struct.unpack_from('<3f', record, 0x1E8), (8.0, 2.0, 8.0))
        self.assertLess(struct.unpack_from('<I', record, 0x370)[0], 24)

    def test_empty_spatial_map_runs_translated_correction_wrapper(self):
        callbacks, query = make_callbacks(mode=1)
        record = make_record(query)
        record[6] = 1
        correction_calls = []

        def adjust(owner, track_index):
            correction_calls.append(('adjust', track_index))
            struct.pack_into('<i', owner, 0x36C, 1)

        callbacks = EnvironmentCallbacks(
            world=callbacks.world, adjust_contact=adjust,
            reset_vehicle_state=lambda _: correction_calls.append(('reset',)),
            vertical_step=4.0)
        environment_step(record, callbacks=callbacks, environment_enabled=True)
        self.assertEqual([item[0] for item in correction_calls], ['adjust', 'reset'])


if __name__ == '__main__':
    unittest.main()
