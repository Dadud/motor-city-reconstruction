import unittest
from client.air_density import calculate_air_density


class AirDensityTests(unittest.TestCase):
    def test_cold_and_weather_increase_density(self):
        base=calculate_air_density(0,False,False,0)
        self.assertGreater(calculate_air_density(0,True,False,0),base)
        self.assertGreater(calculate_air_density(0,False,True,2),base)

    def test_weather_selection_gate(self):
        self.assertEqual(calculate_air_density(0,False,False,2),calculate_air_density(0,False,False,0))

    def test_density_decreases_with_altitude(self):
        self.assertGreater(calculate_air_density(0,False,False,0),calculate_air_density(1000,False,False,0))

    def test_rejects_unverified_table_indices(self):
        for altitude in (-501,5500):
            with self.assertRaises(ValueError): calculate_air_density(altitude,False,False,0)
