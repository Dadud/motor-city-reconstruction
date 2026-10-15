import struct
import unittest
from client.mechanical_loaders import load_tire
from client.tire_templates import build_tire_templates
from tools.tire_loader_oracle import base_component,template_rows
from tools.mechanical_loaders_oracle import initial_configuration


class TireTemplatesTests(unittest.TestCase):
    def test_query_order_and_packed_order_differ(self):
        rows=template_rows(2);rows[1]['Val1']=13.25
        table=build_tire_templates(reversed(rows))
        self.assertEqual(struct.unpack_from('<iii',table,4+0x178),(1,1,1))
        self.assertEqual(struct.unpack_from('<f',table,0x178+16)[0],13.25)
        self.assertEqual(struct.unpack_from('<I',table,0x1d64)[0],2)
        self.assertEqual(table[4+2*0x178:0x1d64],bytes(18*0x178))

    def test_tire_loader_uses_real_tables_and_zero_curve_origins(self):
        table=build_tire_templates(template_rows())
        out=load_tire(initial_configuration(),base_component(1),table)
        self.assertEqual(out.status,0)
        self.assertEqual(struct.unpack_from('<3f',out.configuration,0x124),(205.,75.,15.))
        self.assertEqual(struct.unpack_from('<3f',out.configuration,0x150),(0.,101.,201.))
        self.assertEqual(struct.unpack_from('<2f',out.configuration,0x1b8),(0.,-41.))
        # The original copies TireType as raw integer bits into this field.
        self.assertEqual(struct.unpack_from('<I',out.configuration,0x134)[0],1)
        self.assertEqual(struct.unpack_from('<f',out.configuration,0x144)[0],188.)

    def test_axles_are_separate_and_post_validation_retains_writes(self):
        table=build_tire_templates(template_rows())
        front=load_tire(initial_configuration(),base_component(1),table)
        rows=template_rows();rows[1]['PeakFriction']=3.
        rear=load_tire(front.configuration,base_component(3),build_tire_templates(rows))
        self.assertEqual(rear.status,2)
        self.assertEqual(rear.configuration[0x124:0x228],front.configuration[0x124:0x228])
        self.assertGreater(struct.unpack_from('<f',rear.configuration,0x20)[0],
            struct.unpack_from('<f',front.configuration,0x20)[0])
        self.assertEqual(struct.unpack_from('<f',rear.component,0x1c)[0],1.)

    def test_service_failure_precedes_count_and_authored_bounds_are_explicit(self):
        image=initial_configuration();part=base_component()
        struct.pack_into('<I',part,0x14,0)
        self.assertEqual(load_tire(image,part).status,4)
        self.assertEqual(load_tire(image,part,build_tire_templates([])).status,1)
        part=base_component();struct.pack_into('<f',part,0x48,20.)
        with self.assertRaisesRegex(ValueError,'index'):
            load_tire(image,part,build_tire_templates(template_rows()))
        rows=template_rows(2);rows[1]['TireTypeID']=0
        with self.assertRaisesRegex(ValueError,'identities'):build_tire_templates(rows)
        with self.assertRaisesRegex(ValueError,'twenty'):build_tire_templates(template_rows(21))


if __name__=='__main__':unittest.main()
