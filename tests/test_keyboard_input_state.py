import struct
import unittest

from client.keyboard_input_state import (KEY_RECORD_SIZE, KEY_RECORDS_SIZE,
    KeyboardInputState, update_keyboard_direction_flags)


class KeyboardInputStateTests(unittest.TestCase):
    def make_state(self, mapping=b'\x01\x02\x80', *, mode=5,
                   environment=0, suppressed=0):
        return KeyboardInputState(mapping, bytearray(b'\xa5' * KEY_RECORDS_SIZE),
                                  mode, environment, suppressed)

    def test_missing_records_are_cleared_and_receive_default_threshold_words(self):
        state = self.make_state(mapping=b'\x07\x80')
        flags = update_keyboard_direction_flags(state,
                                                lookup_record=lambda _key, _row: False)
        row = state.records[7 * KEY_RECORD_SIZE:(7 + 1) * KEY_RECORD_SIZE]
        self.assertEqual(flags, 0)
        self.assertEqual(row[:0x50], bytes(0x50))
        self.assertEqual(struct.unpack_from('<8I', row, 0x50), (0x7f,) * 8)
        self.assertEqual(row[0x70:], bytes(0x14))

    def test_signed_direction_thresholds_and_first_active_record_win(self):
        state = self.make_state()
        values = {1: (-100, 126, -1), 2: (1000, 128, 1)}

        def lookup(key, row):
            struct.pack_into('<ii', row, 0, *values[key][:2])
            struct.pack_into('<i', row, 0x70, values[key][2])
            return True

        self.assertEqual(update_keyboard_direction_flags(state,
                         lookup_record=lookup), 4 | 1 | 0x10)

    def test_mode_environment_and_suppression_gates(self):
        for mode, environment, suppressed, expected in (
                (0, 0, 0, 0), (5, 0, 1, 0), (0, 1, 0, 2)):
            state = self.make_state(mapping=b'\x01\x80', mode=mode,
                                    environment=environment,
                                    suppressed=suppressed)

            def lookup(_key, row):
                row[:] = bytes(len(row))
                struct.pack_into('<ii', row, 0, 0x7f, 0x80)
                return True

            self.assertEqual(update_keyboard_direction_flags(
                state, lookup_record=lookup), expected)

    def test_map_requires_sentinel_and_table_is_bounded(self):
        state = self.make_state(mapping=b'\x01\x02')
        with self.assertRaises(ValueError):
            update_keyboard_direction_flags(state, lookup_record=lambda *_: True)
        state = self.make_state()
        state.records = bytearray(KEY_RECORDS_SIZE - 1)
        with self.assertRaises(ValueError):
            update_keyboard_direction_flags(state, lookup_record=lambda *_: True)


if __name__ == '__main__':
    unittest.main()
