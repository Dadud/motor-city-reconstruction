import unittest

from client.travel_map import (TRAVEL_MAP_RESOURCE, TravelMapCache,
                               mark_travel_map)


class TravelMapTests(unittest.TestCase):
    def test_existing_map_sets_only_supported_low_byte_bits(self):
        cache = TravelMapCache(bytearray(4))
        allocate = lambda *_: self.fail('existing map must not allocate')
        mark_travel_map(cache, 19, 0, path_count=60, step_threshold=8,
                        allocate=allocate)
        mark_travel_map(cache, 20, 3, path_count=60, step_threshold=8,
                        allocate=allocate)
        mark_travel_map(cache, 40, 8, path_count=60, step_threshold=8,
                        allocate=allocate)
        mark_travel_map(cache, 60, 1, path_count=60, step_threshold=8,
                        allocate=allocate)
        self.assertEqual(cache.data, bytearray((1, 8, 0, 0)))

    def test_first_call_allocates_and_zeroes_the_exact_resource_table(self):
        cache = TravelMapCache()
        calls = []

        def allocate(resource, size, flags):
            calls.append((resource, size, flags))
            return bytearray([0xa5] * size)

        mark_travel_map(cache, 40, 2, path_count=41, step_threshold=4,
                        allocate=allocate)
        self.assertEqual(calls, [(TRAVEL_MAP_RESOURCE, 3, 0)])
        self.assertEqual(cache.capacity, 3)
        self.assertEqual(cache.data, bytearray((0, 0, 4)))

    def test_failed_allocation_is_retried_on_the_next_call(self):
        cache = TravelMapCache()
        attempts = []

        def allocate(_resource, size, _flags):
            attempts.append(size)
            return None if len(attempts) == 1 else bytearray(size)

        self.assertFalse(mark_travel_map(cache, 3, 1, path_count=20,
            step_threshold=4, allocate=allocate))
        self.assertTrue(mark_travel_map(cache, 3, 1, path_count=20,
            step_threshold=4, allocate=allocate))
        self.assertEqual(attempts, [2, 2])
        self.assertEqual(cache.data, bytearray((2, 0)))


if __name__ == '__main__':
    unittest.main()
