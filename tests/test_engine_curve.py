import struct
import unittest
from unittest.mock import patch
from client.engine_curve import build_assembled_core_record,correct_curve_limits,finalize_engine_configuration
from client.tire_response import f32
from tools.engine_curve_tail_oracle import authored_core


def configuration():
    image=bytearray(0x820)
    for offset,value in ((0x54,9.),(0x430,.1),(0x434,.09),(0x3cc,300.),(0x4d0,2000.)):
        struct.pack_into('<f',image,offset,value)
    for offset,value in ((0x43c,8),(0x70,7000),(0x4cc,12000),(0x570,12000)):
        struct.pack_into('<i',image,offset,value)
    return bytes(image)


class EngineCurveTests(unittest.TestCase):
    def test_electrical_limits_combine_instead_of_multiplying(self):
        curve=(200.,)*25
        for rpm,power,factor in ((12000,2000.,1.),(3000,2000.,.95),
                                (12000,1.,.95),(3000,1.,.85)):
            image=bytearray(configuration());struct.pack_into('<i',image,0x4cc,rpm)
            struct.pack_into('<f',image,0x4d0,power)
            self.assertEqual(correct_curve_limits(image,curve),(f32(200*f32(factor)),)*25)

    def test_valve_limit_uses_next_rpm_denominator(self):
        image=bytearray(configuration());struct.pack_into('<i',image,0x570,4000)
        curve=correct_curve_limits(image,(200.,)*25)
        self.assertEqual(curve[8],200.)
        self.assertEqual(curve[9],f32(200*(4000/5000)**2))

    def test_finalization_preserves_other_fields_and_zeroes_above_limit(self):
        image=configuration()
        with patch('client.engine_curve.build_assembled_core_record',return_value=bytes(1004)):
            final=finalize_engine_configuration(image,{},engine_components_loaded=True,solver=authored_core)
        allowed=set(range(0x80,0xe4))|set(range(0x6c,0x74))|set(range(0x78,0x7c))
        self.assertTrue(all(a==b for k,(a,b) in enumerate(zip(image,final)) if k not in allowed))
        self.assertEqual(struct.unpack_from('<i',final,0x70)[0],6500)
        self.assertEqual(struct.unpack_from('<12f',final,0x80+13*4),(0.,)*12)
        self.assertGreater(struct.unpack_from('<f',final,0x80+8*4)[0],0)

    def test_incomplete_and_unsupported_modes_fail_explicitly(self):
        with self.assertRaisesRegex(ValueError,'complete engine'):
            finalize_engine_configuration(configuration(),{},engine_components_loaded=False)
        for offset,value in ((0x378,1),(0x3d8,1),(0x3c8,6)):
            image=bytearray(configuration());struct.pack_into('<i',image,offset,value)
            with self.assertRaisesRegex(ValueError,'not recovered'):
                build_assembled_core_record(image,{})

    def test_curve_without_idle_crossing_is_rejected(self):
        with patch('client.engine_curve.build_assembled_core_record',return_value=bytes(1004)):
            with self.assertRaisesRegex(ValueError,'idle crossing'):
                finalize_engine_configuration(configuration(),{},engine_components_loaded=True,solver=lambda r:r)

    def test_invalid_curve_shape_and_numbers_are_rejected(self):
        for curve in ((0.,)*24,(float('nan'),)*25):
            with self.assertRaises(ValueError):correct_curve_limits(configuration(),curve)
