from dataclasses import astuple
import struct
import unittest
from client.gear_binding import bind_gear_tables,bind_finalized_gear_tables


class GearBindingTests(unittest.TestCase):
    def fixture(self,rpm=7000,ratios=(2.5,0,2.2,1.7),final=3.5):
        return bind_gear_tables(rpm,205,75,15,ratios,(.8,1,.7,.9)[:len(ratios)],final)

    def test_neutral_sentinel_and_unused_slots(self):
        out=self.fixture()
        self.assertEqual(out.rpm_per_speed[1],0)
        self.assertEqual(out.wheel_inertia_factors[1],0)
        self.assertAlmostEqual(out.speed_per_rpm[1],.01)
        self.assertGreater(out.rpm_per_speed[2],out.rpm_per_speed[3])
        for table in astuple(out)[:-1]:self.assertEqual(table[4:],(0,)*4)

    def test_zero_and_reverse_gearing_branches(self):
        for out in (self.fixture(0),self.fixture(final=0)):
            self.assertEqual(out.rpm_per_speed,(0,)*8)
        self.assertLess(self.fixture(ratios=(-2.5,0,2.2,1.7)).rpm_per_speed[0],0)
        empty=bind_gear_tables(7000,205,75,15,(),(),3.5)
        self.assertEqual(empty.speed_per_rpm,(0,)*8)

    def test_original_zero_denominator_is_explicit(self):
        with self.assertRaisesRegex(ValueError,'near-limit'):
            self.fixture(250)
        with self.assertRaises(ValueError):self.fixture(rpm=True)
        with self.assertRaises(ValueError):bind_gear_tables(7000,205,75,15,(1,),(),3.5)

    def test_finalized_configuration_offsets_and_required_assembly(self):
        image=bytearray(0x820)
        for off,value in ((0x70,7000),(0x32c,4)):struct.pack_into('<i',image,off,value)
        for off,value in ((0x228,205),(0x22c,75),(0x230,15),(0x374,3.5)):
            struct.pack_into('<f',image,off,value)
        struct.pack_into('<4f',image,0x334,2.5,0,2.2,1.7)
        struct.pack_into('<4f',image,0x354,.8,1,.7,.9)
        self.assertEqual(bind_finalized_gear_tables(image,assembly_finalized=True),self.fixture())
        with self.assertRaisesRegex(ValueError,'complete component'):
            bind_finalized_gear_tables(image,assembly_finalized=False)
        struct.pack_into('<i',image,0x32c,9)
        with self.assertRaisesRegex(ValueError,'gear count'):
            bind_finalized_gear_tables(image,assembly_finalized=True)


if __name__=='__main__':unittest.main()
