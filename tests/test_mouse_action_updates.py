import unittest

from client.mouse_action_updates import (
    MouseActionUpdateState, apply_transition_frame, build_transition_mask,
    update_priority_edges, update_special_action_edges,
)


def words(values, count):
    return b''.join(int(value).to_bytes(4, 'little') for value in values) + \
        b'\0' * (4 * (count - len(values)))


class MouseActionUpdateTests(unittest.TestCase):
    def test_priority_edge_selects_first_new_press_and_clears_inactive(self):
        image = words([0x101, 0x102, 0x103], 12)
        latches = bytearray(13)
        calls = []

        def active(action):
            calls.append(action)
            return 1 if action != 0x102 else 0

        self.assertEqual(update_priority_edges(image, latches, dispatch_action=active), 1)
        self.assertEqual(calls, [0x101])
        self.assertEqual(latches[1:4], b'\1\0\0')
        self.assertEqual(update_priority_edges(image, latches,
                                               dispatch_action=lambda _: 0), 0)
        self.assertEqual(latches[1:4], b'\0\0\0')

    def test_transition_mask_orders_first_action_in_bit_zero(self):
        image = words([0x100], 32)
        self.assertEqual(build_transition_mask(image,
            action_active=lambda action: action == 0x100,
            direction_enabled=False, direction_codes=(False,) * 3,
            direction_values=(0,) * 3), 1)

    def test_type_five_and_six_edges_share_native_priority_latches(self):
        latches = bytearray(13)
        self.assertEqual(update_special_action_edges(latches,
            direction_enabled=True, direction_codes=(True, False, False),
            direction_values=(5, 0, 0)), 1)
        self.assertEqual(latches[1], 1)
        self.assertEqual(update_special_action_edges(latches,
            direction_enabled=True, direction_codes=(True, True, False),
            direction_values=(5, 6, 0)), 2)
        self.assertEqual(latches[2], 1)
        self.assertEqual(update_special_action_edges(latches,
            direction_enabled=False, direction_codes=(True, True, False),
            direction_values=(5, 6, 0)), 0)
        self.assertEqual(latches[1:3], b'\0\0')

    def test_direction_action_mapping_occupies_last_four_bits(self):
        values = [0] * 32
        values[27] = 0
        image = words(values, 32)
        result = build_transition_mask(image, action_active=lambda _: 0,
            direction_enabled=True, direction_codes=(True, False, False),
            direction_values=(12, 0, 0))
        self.assertEqual(result, 1 << 27)

    def test_frame_wraps_ring_and_notifies_payload(self):
        state = MouseActionUpdateState(bytearray(13), [0] * 32,
            ring_counter=0xffffffff, notification_payload=b'frame')
        notifications = []
        result = apply_transition_frame(state, words([1], 12), words([1], 32),
            action_active=lambda _: 0x100, priority_action_active=lambda _: 0x100,
            notify=notifications.append)
        self.assertEqual(result, (1, 1, 0))
        self.assertEqual(state.ring_counter, 0)
        self.assertEqual(state.ring_words[0], 1)
        self.assertEqual(notifications, [b'fra\0\1'])

    def test_suppression_skips_notification_but_updates_ring(self):
        state = MouseActionUpdateState(bytearray(13), [0] * 32,
            notification_suppressed=1)
        notifications = []
        apply_transition_frame(state, words([], 12), words([], 32),
            action_active=lambda _: 0, notify=notifications.append)
        self.assertEqual(notifications, [])
        self.assertEqual(state.ring_counter, 1)


if __name__ == '__main__':
    unittest.main()
