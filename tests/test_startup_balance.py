import struct
import unittest
from client.startup_balance import startup_load_coefficient,startup_balance_coefficient,startup_brake_balance,brake_diameter,brake_capacity
from tools.startup_balance_oracle import cases


class StartupBalanceTests(unittest.TestCase):
    def test_complete_table_cases_are_bounded(self):
        values=[startup_balance_coefficient(c) for c in cases()]
        self.assertTrue(all(-10<=v<=10 for v in values))
        self.assertGreater(len(set(values)),10)

    def test_alternate_load_affects_high_load_case(self):
        records=list(cases())
        self.assertTrue(any(startup_balance_coefficient(c)!=startup_balance_coefficient(c,alternate_load=True) for c in records))

    def test_zero_effective_mass_has_zero_load_coefficient(self):
        config=bytearray(next(cases()));config[0x20:0x24]=config[0x28:0x2c]
        self.assertEqual(startup_load_coefficient(config),0.)

    def test_invalid_geometry_and_denominator_rejected(self):
        config=bytearray(next(cases()));struct.pack_into('<f',config,0x2c,0.)
        with self.assertRaises(ValueError):startup_balance_coefficient(config)
        config=bytearray(0x820)
        with self.assertRaises(ValueError):startup_load_coefficient(config)

    def test_brake_capacity_and_diameter_default(self):
        self.assertEqual(brake_diameter(99),brake_diameter(0))
        self.assertGreater(brake_diameter(20),brake_diameter(1))
        base=brake_capacity(.3,0,0,1.,False)
        self.assertEqual(brake_capacity(.3,0,0,.5,False),base*.5)
        self.assertLess(brake_capacity(.3,0,1,1.,True),brake_capacity(.3,0,1,1.,False))

    def test_nonfinite_configuration_rejected(self):
        for value in (float('nan'), float('inf'), -float('inf')):
            config = bytearray(next(cases()))
            struct.pack_into('<f', config, 0x20, value)
            for producer in (startup_load_coefficient, startup_balance_coefficient,
                             startup_brake_balance):
                with self.assertRaises(ValueError):
                    producer(config)

    def test_brake_balance_range_and_parameter_effect(self):
        values=[startup_brake_balance(c) for c in cases()]
        self.assertTrue(all(.1<=v<=1. for v in values))
        self.assertGreater(len(set(values)),5)


if __name__=='__main__':unittest.main()
