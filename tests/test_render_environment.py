import unittest

from client.render_environment import (release_environment_objects,
                                       set_environment_activity)


class RenderEnvironmentTests(unittest.TestCase):
    def test_optional_objects_get_ordered_activity_writes(self):
        self.assertEqual(set_environment_activity(0x1000,0x2000),
                         ((0x1000,1),(0x2000,0)))

    def test_null_objects_are_not_written(self):
        self.assertEqual(set_environment_activity(0,0x2000),
                         (None,(0x2000,0)))
        self.assertEqual(set_environment_activity(0,0),(None,None))

    def test_addresses_must_be_nonnegative_integers(self):
        for value in (-1,1.0,True):
            with self.assertRaises(ValueError):
                set_environment_activity(value,0)

    def test_cleanup_preserves_free_order_and_clears_all_globals(self):
        self.assertEqual(release_environment_objects(
            (0x1000,0,0x3000,0x4000)),
            ((0x1000,0x3000,0x4000),(0,0,0,0)))

    def test_cleanup_rejects_wrong_shape_or_non_word_pointers(self):
        for objects in ((0,0,0), (0,0,0,1<<32), (0,0,0,True)):
            with self.assertRaises(ValueError):
                release_environment_objects(objects)


if __name__=='__main__':
    unittest.main()
