import struct
import unittest
from client.gear_binding import bind_gear_tables
from client.mechanical_loaders import (load_brake,load_engine_block,load_shock,
    load_spring,load_transmission,load_wheel_rim,load_rear_end)
from tools.mechanical_loaders_oracle import base_component,initial_configuration
from tools.mechanical_engine_block_oracle import cases_base


class MechanicalLoaderTests(unittest.TestCase):
    def test_original_transmission_producer_supplies_gear_calculation(self):
        result=load_transmission(initial_configuration(),base_component(130001))
        self.assertEqual(result.status,0)
        rear=load_rear_end(result.configuration,base_component(140001))
        self.assertEqual(rear.status,0)
        image=rear.configuration
        count=struct.unpack_from('<i',image,0x32c)[0]
        ratios=struct.unpack_from('<8f',image,0x334)[:count]
        losses=struct.unpack_from('<8f',image,0x354)[:count]
        final=struct.unpack_from('<f',image,0x374)[0]
        gear=bind_gear_tables(7000,205,75,15,ratios,losses,final)
        self.assertLess(gear.rpm_per_speed[0],0)
        self.assertEqual(gear.rpm_per_speed[1],0)
        self.assertGreater(gear.rpm_per_speed[2],gear.rpm_per_speed[3])
        self.assertEqual(image[0x334:0x354],image[0x698:0x6b8])

    def test_spring_roll_accumulates_once_per_axle_and_preserves_quality(self):
        image=initial_configuration()
        left=load_spring(image,base_component(12001,1))
        right=load_spring(left.configuration,base_component(12001,2))
        self.assertNotEqual(left.configuration[0xfc:0x100],image[0xfc:0x100])
        self.assertEqual(right.configuration[0xfc:0x100],left.configuration[0xfc:0x100])
        self.assertEqual(right.component[0x1c:0x20],base_component(12001,2)[0x1c:0x20])

    def test_brake_minimum_mass_differs_from_stored_component_mass(self):
        component=base_component(10001);struct.pack_into('<f',component,0x30,2.)
        image=initial_configuration();out=load_brake(image,component)
        self.assertEqual(out.status,0)
        self.assertEqual(struct.unpack_from('<f',out.configuration,0x20)[0],579.125)
        self.assertEqual(struct.unpack_from('<f',out.configuration,0x5c8)[0],2.)
        self.assertEqual(struct.unpack_from('<f',out.configuration,0x5e4)[0],300.)

    def test_failure_status_preserves_images_for_these_seven_loaders(self):
        image=initial_configuration()
        for kind,loader in ((10001,load_brake),(11001,load_shock),(12001,load_spring),
                (100001,load_wheel_rim),(130001,load_transmission),(140001,load_rear_end)):
            component=base_component(kind);struct.pack_into('<I',component,0x14,99)
            out=loader(image,component)
            self.assertEqual((out.status,out.configuration,out.component),(1,image,bytes(component)))
            component=base_component(kind);struct.pack_into('<f',component,0x30,0.)
            out=loader(image,component)
            self.assertEqual((out.status,out.configuration,out.component),(2,image,bytes(component)))
        component=bytearray(next(cases_base()));struct.pack_into('<f',component,0x30,0.)
        out=load_engine_block(image,component)
        self.assertEqual((out.status,out.configuration,out.component),(2,image,bytes(component)))

    def test_engine_loader_clears_original_curve_region_and_bounds_text(self):
        component=bytearray(next(cases_base()))
        out=load_engine_block(initial_configuration(),component)
        self.assertEqual(out.status,0)
        self.assertEqual(out.configuration[0x80:0xe4],bytes(100))
        self.assertEqual(struct.unpack_from('<ii',out.configuration,0x6c),(500,7000))
        component[0x120:0x140]=b'x'*32
        with self.assertRaisesRegex(ValueError,'terminator'):
            load_engine_block(initial_configuration(),component)


if __name__=='__main__':unittest.main()
