import struct
import unittest

from client.body_configuration import initialize_body_configuration,stock_body_configuration
from client.physics_data import PhysicsRecord


class BodyConfigurationTests(unittest.TestCase):
    def record(self,**changes):
        args=dict(part_type_id=20001,ordinal=1,mass=420.,values=tuple(i+.5 for i in range(39)))
        args.update(changes)
        return PhysicsRecord(**args)

    def test_mass_is_body_base_and_geometry_comes_from_catalogue(self):
        r=self.record();c=initialize_body_configuration(r)
        self.assertEqual((c.body_mass,c.float_at(0x20)),(420.,420.))
        self.assertEqual((c.wheelbase,c.front_track,c.rear_track),(1.5,2.5,3.5))
        self.assertEqual(c.body_front_weight_fraction,33.5)
        self.assertEqual((c.front_clearance_reference,c.rear_clearance_reference),(30.5,31.5))

    def test_integer_rounding_modes_are_distinct(self):
        c=initialize_body_configuration(self.record())
        self.assertEqual(struct.unpack_from('<i',c.image,0xc)[0],18)
        self.assertEqual(struct.unpack_from('<i',c.image,0x14)[0],38)
        self.assertEqual(struct.unpack_from('<i',c.image,0x44)[0],32)

    def test_unrelated_assembly_fields_remain_untouched(self):
        c=initialize_body_configuration(self.record(),initial_image=b'\xa5'*0x820)
        self.assertEqual(c.image[0x124:],b'\xa5'*(0x820-0x124))
        self.assertEqual(c.image[0xe5:0xe8],b'\xa5'*3)
        self.assertEqual(c.float_at(0x50),9.)

    def test_wrong_shape_rejected(self):
        with self.assertRaises(ValueError):initialize_body_configuration(self.record(values=(0.,)*38))
        with self.assertRaises(ValueError):initialize_body_configuration(self.record(),initial_image=b'')

    def test_stock_join_uses_recovered_ordinal_one(self):
        from types import SimpleNamespace
        class Catalogue:
            physics={(20001,1):self.record()}
            def vehicle(self,identifier):
                assert identifier==101
                return SimpleNamespace(parts=[SimpleNamespace(abstract_type_id=20001,part_type_id=20001,physics_default=0)])
        self.assertEqual(stock_body_configuration(Catalogue()).physics_ordinal,1)


if __name__=='__main__':unittest.main()
