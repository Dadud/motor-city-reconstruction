import struct
import unittest

from client.game_start_flow import GameStartFlow


def image(channel=123):
    result = bytearray(0x5d0)
    struct.pack_into('<I', result, 0x160, channel)
    struct.pack_into('<I', result, 0x5cc, 7)
    return bytes(result)


class GameStartFlowTests(unittest.TestCase):
    def flow(self, result=0):
        flow = GameStartFlow(image())
        self.assertEqual(flow.action.argument, struct.pack('<II', 7, 123))
        flow.enqueued(9)
        flow.completion_queried(result)
        return flow

    def test_worker_success_requires_pump_and_status_success(self):
        flow = self.flow(123)
        self.assertEqual(flow.action.kind, 'pump_application')
        flow.application_pumped(0)
        self.assertEqual((flow.action.kind, flow.action.owner_offset), ('query_room_status', 0x458))
        flow.room_status_queried(4)
        self.assertEqual(flow.action.result, 0)

    def test_negative_worker_result_has_no_status_lookup(self):
        for result in (-1, -51, -0x80000000):
            self.assertEqual(self.flow(result).action.result, result)

    def test_absent_completion_and_abort_do_not_consume_late_result(self):
        flow = GameStartFlow(image())
        flow.enqueued(9)
        flow.completion_queried(None)
        flow.application_pumped(1)
        self.assertEqual(flow.action.result, -51)
        with self.assertRaises(ValueError):
            flow.completion_queried(0)

    def test_pending_status_repeats_pump_and_reads_current_channel(self):
        flow = self.flow()
        flow.application_pumped(0, observed_network_image=image(456))
        self.assertEqual(flow.action.channel_id, 456)
        flow.room_status_queried(255)
        flow.application_pumped(0, observed_network_image=image(789))
        self.assertEqual(flow.action.channel_id, 789)
        flow.room_status_queried(4)
        self.assertEqual(flow.action.result, 0)

    def test_missing_or_failed_room_and_status_phase_abort(self):
        for status, expected in ((None, -7), (8, -20)):
            flow = self.flow()
            flow.application_pumped(0)
            flow.room_status_queried(status)
            self.assertEqual(flow.action.result, expected)
        flow = self.flow()
        flow.application_pumped(-1)
        self.assertEqual(flow.action.result, -51)

    def test_invalid_observations_preserve_action_and_image(self):
        flow = self.flow()
        before = (flow.action, flow.network_image)
        with self.assertRaises(ValueError):
            flow.application_pumped(0, observed_network_image=bytes(0x5d1))
        self.assertEqual((flow.action, flow.network_image), before)
        flow.application_pumped(0)
        before = flow.action
        with self.assertRaises(ValueError):
            flow.room_status_queried(256)
        self.assertEqual(flow.action, before)


if __name__ == '__main__':
    unittest.main()
