import struct
import unittest

from client.keyboard_action_state import (ACTION_TABLE_SIZE, ACTIVE,
    action_progress_value, is_keyboard_action_active)


class KeyboardActionStateTests(unittest.TestCase):
    def test_progress_threshold_modes(self):
        table = bytearray(ACTION_TABLE_SIZE)
        struct.pack_into('<i', table, 0, 50 << 8)
        self.assertEqual(action_progress_value(0x00006401, table), 50)
        self.assertEqual(action_progress_value(0x00000a01, table), ACTIVE)
        struct.pack_into('<i', table, 0, -1 << 8)
        self.assertEqual(action_progress_value(0x000a0001, table), ACTIVE)
        struct.pack_into('<i', table, 0, 50 << 8)
        self.assertEqual(action_progress_value(0x000a3201, table), 80)

    def test_type_one_reports_progress_only_above_0x80(self):
        table = bytearray(ACTION_TABLE_SIZE)
        struct.pack_into('<i', table, 0, 64 << 8)
        common = dict(key_states=bytes(128), direction_flags=0,
                      action_table=table)
        self.assertEqual(is_keyboard_action_active(0x00004001, **common), 0)
        struct.pack_into('<i', table, 0, 65 << 8)
        self.assertEqual(is_keyboard_action_active(0x00004001, **common), ACTIVE)

    def test_direction_actions_observe_held_key_before_direction_mask(self):
        states = bytearray(128)
        states[0x4b] = 1
        self.assertEqual(is_keyboard_action_active(
            0x0000cb04, key_states=states, direction_flags=0,
            action_table=bytes(ACTION_TABLE_SIZE)), ACTIVE)
        states[0x4b] = 0
        self.assertEqual(is_keyboard_action_active(
            0x0000cb04, key_states=states, direction_flags=4,
            action_table=bytes(ACTION_TABLE_SIZE)), ACTIVE)
        self.assertEqual(is_keyboard_action_active(
            0x0000cb04, key_states=states, direction_flags=8,
            action_table=bytes(ACTION_TABLE_SIZE)), 0)

    def test_unhandled_action_uses_external_state_query(self):
        calls = []
        self.assertEqual(is_keyboard_action_active(
            0x12345602, key_states=bytes(128), direction_flags=0,
            action_table=bytes(ACTION_TABLE_SIZE),
            query_other_action=lambda action: calls.append(action) or 0x1234),
            0x1234)
        self.assertEqual(calls, [0x12345602])


if __name__ == '__main__':
    unittest.main()
