import unittest
from client.scheduler import ScheduledCall, insert_callback, execute_callbacks, execute_batch, selected_iterations, pending_iterations


class SchedulerTests(unittest.TestCase):
    def test_stable_signed_priority(self):
        entries = []
        for priority, callback in ((30, 1), (-1, 2), (30, 3), (6, 4)):
            insert_callback(entries, ScheduledCall(priority, callback, 0))
        self.assertEqual([e.callback for e in entries], [2, 4, 1, 3])

    def test_executor_reads_later_mutation_and_snapshots_count(self):
        entries = [ScheduledCall(6, 1, 10), ScheduledCall(30, 2, 20)]
        calls = []
        def dispatch(callback, payload):
            calls.append((callback, payload))
            if len(calls) == 1:
                entries[1] = ScheduledCall(30, 3, 30)
                entries.append(ScheduledCall(40, 4, 40))
        execute_callbacks(entries, dispatch)
        self.assertEqual(calls, [(1, 10), (3, 30)])

    def test_null_callback_skipped(self):
        calls = []
        execute_callbacks([ScheduledCall(0, 0, 55)], lambda *args: calls.append(args))
        self.assertEqual(calls, [])

    def test_batch_interleaving_and_wrap(self):
        calls = []
        result = execute_batch(0xffffffff, 2, False, lambda: calls.append('first'),
                               lambda: calls.append('second'), lambda: calls.append('after'))
        self.assertEqual(result, 1)
        self.assertEqual(calls, ['second', 'after', 'first', 'second', 'after'])

    def test_selector_signed_boundaries(self):
        self.assertEqual(selected_iterations(True, 0, -4), 1)
        self.assertEqual(selected_iterations(True, 0, -3), 0)
        self.assertEqual(selected_iterations(True, 1, -2), 1)
        self.assertEqual(selected_iterations(True, 3, -2), 2)
        self.assertEqual(selected_iterations(False, 0, 1), 1)

    def test_inhibited_batch_does_not_call(self):
        def fail(): self.fail('inhibited batch dispatched')
        self.assertEqual(execute_batch(6, 2, True, fail, fail, fail), 6)

    def test_invalid_boundaries(self):
        with self.assertRaises(ValueError): ScheduledCall(1 << 31, 1, 0)
        with self.assertRaises(ValueError): ScheduledCall(0, -1, 0)
        with self.assertRaises(ValueError): execute_batch(0, 3, False, lambda: None, lambda: None, lambda: None)
        entries = [ScheduledCall(0, 1, 0), ScheduledCall(0, 2, 0)]
        with self.assertRaises(ValueError): execute_callbacks(entries, lambda *_: entries.clear())

    def test_catchup_limit_and_wrap(self):
        self.assertEqual(pending_iterations(40, 3), 16)
        self.assertEqual(pending_iterations(3, 40), 0)
        self.assertEqual(pending_iterations(0, 0xffffffff), 1)
        self.assertEqual(pending_iterations(0x80000000, 0), 0)
