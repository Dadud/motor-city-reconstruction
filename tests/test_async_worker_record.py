import struct
import unittest

from client.async_worker_record import stamp_operation, store_worker_result


class AsyncWorkerRecordTests(unittest.TestCase):
    def test_tracked_ids_wrap_skip_zero_and_preserve_other_fields(self):
        raw = struct.pack('<III', 7, 0xaaaaaaaa, 0xbbbbbbbb) + bytes(range(256))
        for counter, expected in ((0, 1), (1, 2), (0xfffffffe, 0xffffffff), (0xffffffff, 1)):
            output = stamp_operation(raw, counter=counter, tracked=True)
            self.assertEqual((output.counter, output.operation_id), (expected, expected))
            self.assertEqual(output.record[:4], raw[:4])
            self.assertEqual(output.record[8:], raw[8:])
            self.assertEqual(struct.unpack_from('<I', output.record, 4)[0], expected)

    def test_untracked_preserves_counter_and_clears_only_id(self):
        raw = bytes([255]) * 12
        output = stamp_operation(raw, counter=0xffffffff, tracked=False)
        self.assertEqual(output.counter, 0xffffffff)
        self.assertEqual(output.operation_id, 0)
        self.assertEqual(output.record, raw[:4] + bytes(4) + raw[8:])

    def test_missing_manager_and_null_record_do_not_write(self):
        raw = bytes([255]) * 12
        for record, manager in ((None, True), (None, False), (raw, False)):
            output = stamp_operation(record, counter=9, tracked=True, manager_present=manager)
            self.assertEqual((output.record, output.counter, output.operation_id), (record, 9, 0))

    def test_result_written_for_tracked_and_untracked_work(self):
        for operation_id in (0, 1, 0xffffffff):
            raw = struct.pack('<III', 0, operation_id, 123) + b'argument'
            output, queued = store_worker_result(raw, 0xfffffffa)
            self.assertEqual(queued, operation_id != 0)
            self.assertEqual(output[:8], raw[:8])
            self.assertEqual(output[12:], raw[12:])
            self.assertEqual(struct.unpack_from('<I', output, 8)[0], 0xfffffffa)

    def test_bounded_portable_inputs(self):
        for raw in (b'', bytes(11), bytearray(12)):
            with self.assertRaises(ValueError):
                stamp_operation(raw, counter=0, tracked=True)
            with self.assertRaises(ValueError):
                store_worker_result(raw, 0)
        for bits in (-1, 0x100000000, True):
            with self.assertRaises(ValueError):
                stamp_operation(bytes(12), counter=bits, tracked=True)
            with self.assertRaises(ValueError):
                store_worker_result(bytes(12), bits)
