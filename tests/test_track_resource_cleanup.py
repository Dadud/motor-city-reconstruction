import unittest

from client.track_resource_cleanup import (
    AUXILIARY_RESOURCE, TRACK_BASE_POINTER, TRACK_MODE_FLAG,
    TRACK_RESOURCE_A, TRACK_RESOURCE_B, TRACK_RESOURCE_COUNT,
    close_track_loader_globals, release_track_loader_globals,
)


class TrackResourceCleanupTests(unittest.TestCase):
    def test_loader_cleanup_releases_slots_in_native_order(self):
        globals_ = {
            TRACK_RESOURCE_COUNT: 7,
            TRACK_RESOURCE_A: 'alloc-a',
            TRACK_RESOURCE_B: 'alloc-b',
            TRACK_BASE_POINTER: 'interior-pointer',
        }
        released = []
        release_track_loader_globals(globals_, released.append)
        self.assertEqual(released, ['alloc-a', 'alloc-b'])
        self.assertEqual(globals_, {
            TRACK_RESOURCE_COUNT: 0,
            TRACK_RESOURCE_A: 0,
            TRACK_RESOURCE_B: 0,
            TRACK_BASE_POINTER: 0,
        })

    def test_wrapper_clears_flag_and_releases_auxiliary_last(self):
        globals_ = {
            TRACK_MODE_FLAG: 1,
            TRACK_RESOURCE_COUNT: 2,
            TRACK_RESOURCE_A: 'a',
            TRACK_RESOURCE_B: 0,
            TRACK_BASE_POINTER: 'base',
            AUXILIARY_RESOURCE: 'aux',
        }
        released = []
        close_track_loader_globals(globals_, released.append)
        self.assertEqual(released, ['a', 'aux'])
        self.assertEqual(globals_[TRACK_MODE_FLAG], 0)
        self.assertEqual(globals_[AUXILIARY_RESOURCE], 0)
        self.assertEqual(globals_[TRACK_BASE_POINTER], 0)

    def test_null_resources_are_not_released(self):
        globals_ = {TRACK_RESOURCE_A: None, TRACK_RESOURCE_B: 0}
        released = []
        release_track_loader_globals(globals_, released.append)
        self.assertEqual(released, [])
        self.assertEqual(globals_[TRACK_RESOURCE_COUNT], 0)
        self.assertEqual(globals_[TRACK_BASE_POINTER], 0)


if __name__ == '__main__':
    unittest.main()
