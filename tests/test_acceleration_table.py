import struct
import unittest
from client.acceleration_table import acceleration_table,startup_force
from tools.acceleration_table_oracle import cases


class AccelerationTableTests(unittest.TestCase):
    def test_range_and_limits(self):
        config,record=next(cases())
        output=acceleration_table(config,record)
        self.assertEqual(len(output),0x4a8)
        self.assertEqual(output[:0x128],record[:0x128]) # bytes below the outputs stay unchanged
        primary=struct.unpack_from('<112f',output,0x128)
        secondary=struct.unpack_from('<112f',output,0x2e8)
        self.assertTrue(all(value>=0 for value in primary+secondary))

    def test_helper_easing_window(self):
        config,record=next(cases())
        gated=bytearray(config);struct.pack_into('<i',gated,0x68c,1)
        gated=bytes(gated)
        mid=startup_force(gated,record,1500,2,5.)
        edge=startup_force(gated,record,1500,2,10.)
        past=startup_force(gated,record,1500,2,10.001)
        self.assertGreater(mid,past) # (1-t)t^3*1.5 boosts effective torque inside the window
        self.assertLess(edge,past) # stored binary32 0.1 leaves t slightly above one at sample ten
        self.assertEqual(past,startup_force(config,record,1500,2,5.)) # gate off at 0x68c=0 matches uneased values
        self.assertEqual(mid,startup_force(gated,record,1500,2,5.,True)) # sixth ABI argument is unused

    def test_reject_invalid(self):
        config,record=next(cases())
        for args in ((config[:-1],record),(config,record[:-1])):
            with self.assertRaises(ValueError):acceleration_table(*args)
            with self.assertRaises(ValueError):startup_force(*args,800,0,0.)
        for rpm in (0,12001):
            with self.assertRaises(ValueError):startup_force(config,record,rpm,0,0.)
        with self.assertRaises(ValueError):startup_force(config,record,800,8,0.)
        with self.assertRaises(ValueError):startup_force(config,record,800.0,0,0.)
        shallow=bytearray(record)
        for i in range(8):struct.pack_into('<f',shallow,0xac+i*4,0.)
        with self.assertRaises(ValueError):acceleration_table(config,bytes(shallow))
        no_mass=bytearray(config);struct.pack_into('<f',no_mass,0x20,0.)
        with self.assertRaises(ValueError):acceleration_table(bytes(no_mass),record)
        no_idle=bytearray(config);struct.pack_into('<i',no_idle,0x6c,0)
        with self.assertRaises(ValueError):acceleration_table(bytes(no_idle),record)
