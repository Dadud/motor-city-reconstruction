import struct
import unittest
from client.room_disconnect_flow import RoomDisconnectFlow
from client.async_worker_record import stamp_operation, store_worker_result
from client.async_worker_completion import CompletedOperation, WorkerCompletionQueue


class RoomDisconnectFlowTests(unittest.TestCase):
    def image(self, connected=1, pending=0):
        image = bytearray([0xa5]*0x3c0)
        struct.pack_into('<H', image, 0xec, connected)
        struct.pack_into('<I', image, 0x3a8, pending)
        struct.pack_into('<I', image, 0x39c, 7)
        struct.pack_into('<I', image, 0xc0, 99)
        return bytes(image)

    def ready(self, wait=True):
        image = self.image()
        flow = RoomDisconnectFlow(image, wait_for_completion=wait)
        self.assertEqual((flow.action.kind, flow.action.owner_offset), ('reset_container', 0x2e0))
        flow.container_reset(image)
        self.assertEqual((flow.action.kind, flow.action.owner_offset), ('reset_container', 0x1fc))
        flow.container_reset(image)
        self.assertEqual(flow.action.kind, 'enqueue')
        self.assertEqual(flow.action.argument, struct.pack('<II', 7, 99))
        self.assertEqual(flow.room_image[0xec:0xee], bytes(2))
        return flow

    def test_pending_wait_does_not_recheck_connected_until_pending_clears(self):
        image = self.image(pending=1)
        flow = RoomDisconnectFlow(image, wait_for_completion=True)
        flow.container_reset(image)
        flow.container_reset(image)
        self.assertEqual(flow.action.kind, 'yield_pending')
        flow.pending_yielded(self.image(0, 1))
        self.assertEqual(flow.action.kind, 'yield_pending')
        flow.pending_yielded(self.image(0, 0))
        self.assertEqual((flow.action.kind, flow.action.result), ('complete', 0))

    def test_disconnected_pending_state_does_not_wait_or_enqueue(self):
        image = self.image(0, 9)
        flow = RoomDisconnectFlow(image, wait_for_completion=True)
        flow.container_reset(image)
        flow.container_reset(image)
        self.assertEqual((flow.action.kind, flow.action.result), ('complete', 0))
        self.assertEqual(struct.unpack_from('<I', flow.room_image, 0x3a8)[0], 9)

    def test_tracked_queries_first_and_returns_signed_completion(self):
        flow = self.ready()
        flow.enqueued(0xffffffff)
        self.assertEqual((flow.action.kind, flow.action.operation_id), ('query_completion', 0xffffffff))
        flow.completion_queried(None)
        self.assertEqual(flow.action.kind, 'pump_application')
        flow.application_pumped(0)
        self.assertEqual(flow.action.kind, 'query_completion')
        flow.completion_queried(-6)
        self.assertEqual((flow.action.kind, flow.action.result), ('complete', -6))

    def test_application_abort_ends_without_another_query(self):
        for result in (-1, 1, -0x80000000, 0x7fffffff):
            flow = self.ready()
            flow.enqueued(2)
            flow.completion_queried(None)
            image = flow.room_image
            flow.application_pumped(result)
            self.assertEqual((flow.action.kind, flow.action.result), ('complete', -51))
            self.assertEqual(flow.room_image, image)
            with self.assertRaises(ValueError):
                flow.completion_queried(0)

    def test_untracked_finishes_after_enqueue_without_reading_record_id(self):
        flow = self.ready(False)
        self.assertFalse(flow.action.tracked)
        flow.enqueued()
        self.assertEqual((flow.action.kind, flow.action.result), ('complete', 0))

    def test_bad_observations_leave_current_request_unchanged(self):
        flow = self.ready()
        for operation_id in (0, True, -1, 0x100000000):
            with self.assertRaises(ValueError):
                flow.enqueued(operation_id)
            self.assertEqual(flow.action.kind, 'enqueue')
        with self.assertRaises(ValueError):
            flow.container_reset(self.image())
        flow.enqueued(1)
        with self.assertRaises(ValueError):
            flow.completion_queried(True)
        self.assertEqual(flow.action.kind, 'query_completion')

    def test_owned_queue_completion_connects_to_flow_without_losing_other_results(self):
        flow = self.ready()
        # Padding is authored owned storage; original stack tail is unspecified.
        record = struct.pack('<III', 1, 0, 0) + flow.action.argument + bytes(2040)
        stamped = stamp_operation(record, counter=0xffffffff, tracked=True)
        self.assertEqual(stamped.operation_id, 1)
        flow.enqueued(struct.unpack_from('<I', stamped.record, 4)[0])
        unrelated = struct.pack('<III', 9, 2, 0) + bytes(2048)
        queue = WorkerCompletionQueue((unrelated,))
        missing = queue.query(flow.action.operation_id)
        self.assertFalse(missing.found)
        flow.completion_queried(None)
        completed_record, should_queue = store_worker_result(stamped.record, 0xfffffffa)
        self.assertTrue(should_queue)
        queue.append(completed_record)
        flow.application_pumped(0)
        completed = CompletedOperation.from_record(queue.query(flow.action.operation_id).record)
        flow.completion_queried(completed.result)
        self.assertEqual((flow.action.kind, flow.action.result), ('complete', -6))
        self.assertEqual(queue.records, (unrelated,))

    def test_abort_does_not_consume_a_completion_that_arrives_during_pump(self):
        flow = self.ready()
        flow.enqueued(7)
        queue = WorkerCompletionQueue()
        self.assertFalse(queue.query(flow.action.operation_id).found)
        flow.completion_queried(None)
        late_record = struct.pack('<III', 1, 7, 0) + bytes(2048)
        queue.append(late_record)
        flow.application_pumped(1)
        self.assertEqual(flow.action.result, -51)
        self.assertEqual(queue.records, (late_record,))
