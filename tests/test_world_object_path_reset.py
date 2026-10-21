import struct
import unittest

from client.world_object_path_reset import (PathResetGlobals,
                                            advance_reset_axis,
                                            update_path_reset_state)


class WorldObjectPathResetTests(unittest.TestCase):
    def test_advance_axis_xors_only_the_two_reset_direction_bits(self):
        record = bytearray(0x1c98)
        struct.pack_into('<I', record, 0xdf4, 0x13570012)
        advance_reset_axis(record)
        self.assertEqual(struct.unpack_from('<I', record, 0xdf4)[0],
                         0x13570c12)
        advance_reset_axis(record)
        self.assertEqual(struct.unpack_from('<I', record, 0xdf4)[0],
                         0x13570012)

    def setUp(self):
        self.globals_ = PathResetGlobals(
            path_count=60, wrap_reference=10, secondary_reference=30,
            multi_segment=0, step_threshold=4, designated_mode=2,
            environment_mode=1)

    def test_interface_gate_preserves_owner_when_service_handles_change(self):
        record = bytearray(b'\xa5' * 0x1c98)
        before = bytes(record)
        result = update_path_reset_state(record, globals_=self.globals_,
            interface_query=lambda selector, owner: int(selector == 0x16 and owner is record),
            notify_track_change=lambda *_: self.fail('unexpected notification'),
            advance_state=lambda _: self.fail('unexpected advance'))
        self.assertEqual(bytes(result), before)

    def test_identical_path_indices_leave_owner_untouched(self):
        record = bytearray(b'\xa5' * 0x1c98)
        struct.pack_into('<i', record, 0x364, 17)
        struct.pack_into('<i', record, 0x370, 17)
        before = bytes(record)
        update_path_reset_state(record, globals_=self.globals_,
            interface_query=lambda *_: 0,
            notify_track_change=lambda *_: self.fail('unchanged path notified'),
            advance_state=lambda _: self.fail('unchanged path advanced'))
        self.assertEqual(bytes(record), before)


if __name__ == '__main__':
    unittest.main()
