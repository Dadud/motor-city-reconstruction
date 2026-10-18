import struct
import unittest
from client.gear_force_table import gear_force_table
from tools.gear_force_table_oracle import cases


class GearForceTests(unittest.TestCase):
    def test_range_and_limits(self):
        config,steps=next(cases())
        output=gear_force_table(config,steps,0)
        self.assertEqual(len(output),135)
        self.assertEqual(len(set(output)),1) # negative input samples clamp to zero RPM
        limited=bytearray(config);struct.pack_into('<ii',limited,0x6c,800,6500)
        self.assertEqual(gear_force_table(limited,steps,0),(0.,)*135)

    def test_reject_invalid(self):
        config,steps=next(cases())
        for args in ((config[:-1],steps,0),(config,steps,8),(config,steps[:-1],0)):
            with self.assertRaises(ValueError):gear_force_table(*args)
        c=bytearray(config);struct.pack_into('<f',c,0x228,float('nan'))
        with self.assertRaises(ValueError):gear_force_table(c,steps,0)
