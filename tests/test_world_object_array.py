import unittest

from client.world_object_array import update_active_world_objects


class WorldObjectArrayTests(unittest.TestCase):
    def test_dispatches_active_rows_in_original_order(self):
        calls = []
        update_active_world_objects(0x1000, (True, False, True), calls.append)
        self.assertEqual(calls, [0x1000, 0x19F0])

    def test_zero_count_does_not_call_handler(self):
        update_active_world_objects(0x1000, (), lambda _: self.fail('empty array dispatched'))

    def test_requires_supported_handler_and_valid_rows(self):
        with self.assertRaisesRegex(ValueError, 'callback is required'):
            update_active_world_objects(0x1000, (), None)
        for base, flags in ((0, (True,)), (0x1000, (True, 1)),
                            (0xffffff00, (True, True))):
            with self.subTest(base=base, flags=flags), self.assertRaises(ValueError):
                update_active_world_objects(base, flags, lambda _: None)


if __name__ == '__main__':
    unittest.main()
