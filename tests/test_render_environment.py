import unittest

from client.render_environment import set_environment_activity


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


if __name__=='__main__':
    unittest.main()
