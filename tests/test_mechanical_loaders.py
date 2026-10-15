import struct
import unittest
from client.gear_binding import bind_gear_tables
from client.mechanical_loaders import (load_brake,load_engine_block,load_shock,
    load_spring,load_transmission,load_wheel_rim,load_rear_end)
from tools.mechanical_loaders_oracle import base_component,initial_configuration
from tools.mechanical_engine_block_oracle import cases_base
from client.mechanical_loaders import (load_crankshaft,load_connecting_rods,
    load_cylinder_head,load_pistons,load_valve_train,load_camshaft)
from tools.engine_component_loaders_oracle import base_component as engine_part,configuration


class MechanicalLoaderTests(unittest.TestCase):
    def test_engine_family_rejection_keeps_original_mutation_order(self):
        image=configuration(family=4)
        for kind,loader,mutates in ((180001,load_crankshaft,True),
                (190001,load_connecting_rods,True),(1000001,load_cylinder_head,False),
                (200001,load_pistons,False),(1100001,load_camshaft,False),
                (1200001,load_valve_train,False)):
            part=engine_part(kind);out=loader(image,part)
            self.assertEqual(out.status,2)
            self.assertEqual(out.component,bytes(part))
            self.assertEqual(out.configuration!=image,mutates)
            if mutates:
                self.assertGreater(struct.unpack_from('<f',out.configuration,0x20)[0],575.125)
            struct.pack_into('<I',part,0x14,99)
            out=loader(image,part)
            self.assertEqual((out.status,out.configuration),(1,image))

    def test_head_then_pistons_build_compression_and_per_cylinder_mass(self):
        head=load_cylinder_head(configuration(),engine_part(1000001))
        piston=load_pistons(head.configuration,engine_part(200001))
        self.assertEqual((head.status,piston.status),(0,0))
        self.assertEqual(struct.unpack_from('<f',piston.configuration,0x54)[0],8.25)
        self.assertAlmostEqual(struct.unpack_from('<f',piston.configuration,0x478)[0],4.8,places=5)
        self.assertAlmostEqual(struct.unpack_from('<f',piston.configuration,0x20)[0],619.925,places=4)

    def test_material_validation_truncates_but_quality_rounds(self):
        part=engine_part(200001);struct.pack_into('<f',part,0x40,7.9)
        accepted=load_pistons(configuration(),part)
        self.assertEqual(accepted.status,0)
        self.assertAlmostEqual(struct.unpack_from('<f',accepted.component,0x1c)[0],.93)
        struct.pack_into('<f',part,0x40,8.)
        self.assertEqual(load_pistons(configuration(),part).status,2)

    def test_valve_final_value_truncates_without_rounding(self):
        part=engine_part(1200001);struct.pack_into('<f',part,0x44,15.9)
        result=load_valve_train(configuration(),part)
        self.assertEqual(result.status,0)
        self.assertEqual(struct.unpack_from('<i',result.configuration,0x570)[0],15)

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
