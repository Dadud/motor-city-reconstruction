import struct
import unittest

from client.owner_binding import bind_owner_inertia,bind_axle_levers,bind_finalized_owner,body_inertia_scales,bind_startup_com


class OwnerBindingTests(unittest.TestCase):
    def test_shape_selector_groups(self):
        self.assertEqual(body_inertia_scales(2),body_inertia_scales(0))
        self.assertEqual(body_inertia_scales(3),body_inertia_scales(7))
        self.assertEqual(body_inertia_scales(99),(1.,1.,1.))
        self.assertNotEqual(body_inertia_scales(6),body_inertia_scales(5))

    def test_unknown_shape_preserves_supplied_scales(self):
        self.assertEqual(body_inertia_scales(99,(2.,3.,4.)),(2.,3.,4.))

    def test_mass_zero_fallback_is_original(self):
        r=bind_owner_inertia(0.,(1.,1.,1.),2)
        self.assertEqual(r.mass,1000.)

    def test_lever_distribution_uses_completed_fraction(self):
        r=bind_axle_levers(4.,.25)
        self.assertEqual((r.front,r.rear),(3.,1.))

    def test_inertia_scales_with_mass(self):
        a=bind_owner_inertia(500.,(1.,1.,1.),2)
        b=bind_owner_inertia(1000.,(1.,1.,1.),2)
        self.assertEqual(b.inertia,tuple(v*2 for v in a.inertia))

    def test_body_only_configuration_refused(self):
        with self.assertRaises(ValueError):bind_finalized_owner(bytes(0x820),(1.,1.,1.),assembly_finalized=False)

    def test_finalized_fields_read_from_recovered_offsets(self):
        c=bytearray(0x820)
        for offset,value in ((0x20,800.),(0x2c,4.),(0x3c,.25)):
            struct.pack_into('<f',c,offset,value)
        struct.pack_into('<i',c,0x48,2)
        r=bind_finalized_owner(c,(1.,1.,1.),assembly_finalized=True)
        self.assertEqual(r.inertia.mass,800.)
        self.assertEqual((r.axle_levers.front,r.axle_levers.rear),(3.,1.))

    def test_com_preserves_existing_front_lever_observation(self):
        r=bind_startup_com(1.1,1.,2.,.75)
        self.assertAlmostEqual(r.vertical,0.,places=6)
        self.assertEqual(r.longitudinal,1.25)


if __name__=='__main__':unittest.main()
