import struct
import unittest
from client.assembly_finalization import finalize_loaded_configuration
from client.assembly_weight import assembled_front_weight_fraction,finalize_weight_distribution
from client.owner_binding import bind_finalized_owner
from client.tire_response import f32
from tools.assembly_finalization_oracle import cases


class AssemblyFinalizationTests(unittest.TestCase):
    def test_paired_component_mass_changes_assembled_axle_fraction(self):
        front=[0.]*23;rear=[0.]*13
        self.assertEqual(assembled_front_weight_fraction(1000,.5,2.5,0,front,rear),.5)
        front[4]=250
        self.assertEqual(assembled_front_weight_fraction(1000,.5,2.5,0,front,rear),2/3)
        rear[1]=250
        self.assertEqual(assembled_front_weight_fraction(1000,.5,2.5,0,front,rear),.5)

    def test_shared_component_has_asymmetric_weight(self):
        self.assertEqual(assembled_front_weight_fraction(1000,.5,2.5,1000,[0.]*23,[0.]*13),.375)

    def test_finalized_fraction_reaches_owner_axle_binding(self):
        image=bytearray(next(cases()))
        struct.pack_into('<i',image,0x48,2)
        struct.pack_into('<f',image,0x40,.4305)
        struct.pack_into('<f',image,0x5c8,250.)
        final=finalize_loaded_configuration(image,components_loaded=True)
        owner=bind_finalized_owner(final,(1.,.7,2.),assembly_finalized=True)
        fraction=struct.unpack_from('<f',final,0x3c)[0]
        self.assertNotEqual(fraction,f32(.4305))
        self.assertEqual(owner.axle_levers.rear,f32(fraction*.125))
        self.assertEqual(owner.inertia.mass,975.25)
        self.assertEqual(final[0x20:0x24],image[0x20:0x24])

    def test_clearance_override_requires_both_values(self):
        image=bytearray(next(cases()))
        original=bytes(image[0x114:0x11c])
        struct.pack_into('<f',image,0x610,.17)
        final=finalize_loaded_configuration(image,components_loaded=True)
        self.assertEqual(final[0x114:0x11c],original)
        struct.pack_into('<f',image,0x620,.31)
        final=finalize_loaded_configuration(image,components_loaded=True)
        self.assertEqual(final[0x114:0x118],image[0x610:0x614])
        self.assertEqual(final[0x118:0x11c],image[0x620:0x624])

    def test_incomplete_and_malformed_assembly_stays_explicit(self):
        image=bytearray(next(cases()))
        for function in (finalize_loaded_configuration,finalize_weight_distribution):
            with self.assertRaisesRegex(ValueError,'component loading'):
                function(image,components_loaded=False)
            with self.assertRaisesRegex(ValueError,'0x820'):
                function(b'',components_loaded=True)
        struct.pack_into('<i',image,0x444,10)
        with self.assertRaisesRegex(ValueError,'selector'):
            finalize_loaded_configuration(image,components_loaded=True)
        with self.assertRaisesRegex(ValueError,'mass moment'):
            assembled_front_weight_fraction(0,.5,2.5,0,[0.]*23,[0.]*13)
        with self.assertRaisesRegex(ValueError,'finite'):
            assembled_front_weight_fraction(1000,float('nan'),2.5,0,[0.]*23,[0.]*13)


if __name__=='__main__':unittest.main()
