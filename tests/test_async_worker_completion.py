import struct
import unittest

from client.async_worker_completion import (
    CompletedOperation, WorkerCompletionQueue, WORKER_RECORD_SIZE)


def record(operation_id, marker, result=0):
    return struct.pack('<III', 7, operation_id, result) + bytes([marker]) * (WORKER_RECORD_SIZE - 12)


class WorkerCompletionTests(unittest.TestCase):
    def test_first_matching_completion_and_preserved_remaining_order(self):
        original = (record(1, 1), record(2, 2), record(1, 3), record(3, 4))
        queue = WorkerCompletionQueue(original)
        result = queue.query(1)
        self.assertTrue(result.found)
        self.assertEqual(result.record, original[0])
        self.assertEqual(queue.records, original[1:])
        self.assertEqual(queue.query(1).record, original[2])
        self.assertEqual(queue.records, (original[1], original[3]))

    def test_no_match_and_empty_leave_state_unchanged(self):
        queue = WorkerCompletionQueue((record(0, 1), record(2, 2)))
        before = queue.records
        self.assertFalse(queue.query(1).found)
        self.assertEqual(queue.records, before)
        self.assertFalse(WorkerCompletionQueue().query(0xffffffff).found)

    def test_null_output_still_removes_completion(self):
        queue = WorkerCompletionQueue((record(1, 1), record(2, 2)))
        result = queue.query(2, copy_output=False)
        self.assertTrue(result.found)
        self.assertIsNone(result.record)
        self.assertEqual(queue.records, (record(1, 1),))

    def test_append_and_complete_signed_returns(self):
        queue = WorkerCompletionQueue()
        for bits, expected in ((0, 0), (1, 1), (0x7fffffff, 0x7fffffff),
                               (0x80000000, -2147483648), (0xffffffff, -1)):
            queue.append(record(0xffffffff, 9, bits))
            completed = CompletedOperation.from_record(queue.query(0xffffffff).record)
            self.assertEqual((completed.kind, completed.operation_id, completed.result),
                             (7, 0xffffffff, expected))
            self.assertEqual(completed.argument, bytes([9]) * 2048)

    def test_invalid_query_and_record_boundaries(self):
        queue = WorkerCompletionQueue((record(1, 1),))
        before = queue.records
        for operation_id in (0, -1, True, 0x100000000, '1'):
            with self.assertRaises(ValueError):
                queue.query(operation_id)
        self.assertEqual(queue.records, before)
        with self.assertRaises(TypeError):
            queue.query(1, copy_output=1)
        for raw in (b'', bytes(WORKER_RECORD_SIZE - 1), bytes(WORKER_RECORD_SIZE + 1),
                    bytearray(WORKER_RECORD_SIZE)):
            with self.assertRaises(ValueError):
                queue.append(raw)
            with self.assertRaises(ValueError):
                WorkerCompletionQueue((raw,))
            with self.assertRaises(ValueError):
                CompletedOperation.from_record(raw)
