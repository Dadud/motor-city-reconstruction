import unittest

from client.startup_resistance import startup_resistance_table, startup_surface_factor


class StartupResistanceTests(unittest.TestCase):
    def test_surface_threshold_and_selector_groups(self):
        self.assertEqual(startup_surface_factor(2, .99999994), 0.)
        self.assertGreater(startup_surface_factor(2, 1.), 0.)
        self.assertEqual(startup_surface_factor(3, 33.), startup_surface_factor(5, 33.))
        self.assertEqual(startup_surface_factor(0, 33.), startup_surface_factor(0xffffffff, 33.))

    def test_complete_table_and_separate_contributions(self):
        zero = startup_resistance_table(0., 0., 0., 0)
        self.assertEqual(zero, (0.,) * 135)
        aerodynamic = startup_resistance_table(0., .3, 2., 0)
        self.assertEqual(aerodynamic[20], aerodynamic[10] * 4.)
        rolling = startup_resistance_table(1000., 0., 0., 2)
        self.assertEqual(rolling[0], 0.)
        self.assertGreater(rolling[134], rolling[1])

    def test_invalid_observations_rejected(self):
        for value in (float('inf'), float('nan')):
            with self.assertRaises(ValueError):
                startup_surface_factor(0, value)
            with self.assertRaises(ValueError):
                startup_resistance_table(value, .3, 2., 0)
        with self.assertRaises(ValueError):
            startup_surface_factor(-1, 10.)


if __name__ == '__main__':
    unittest.main()
