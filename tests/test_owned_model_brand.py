import struct
import unittest
from client.owned_parts import apply_owned_model_brand, apply_owned_vehicle_price


class OwnedModelBrandTests(unittest.TestCase):
    def test_final_vehicle_price_override_is_specific_to_type_101(self):
        initial = bytearray(b'Z'*1596)
        struct.pack_into('<i',initial,0,101)
        output = apply_owned_vehicle_price(bytes(initial))
        self.assertEqual(struct.unpack_from('<i',output,0x1eb)[0],0)
        self.assertEqual(output[0x1ef:],initial[0x1ef:])
        struct.pack_into('<i',initial,0,20001)
        self.assertEqual(apply_owned_vehicle_price(bytes(initial)),bytes(initial))

    def test_model_brand_replaces_family_prefix_and_preserves_tail(self):
        initial = bytearray(b'Z'*1596)
        initial[0x2c7:0x2d4] = b'Family brand\0'
        initial = bytes(initial)
        output = apply_owned_model_brand(initial,dict(Brand='Maker',PicName='pic'),text_encoding='cp1252')
        self.assertEqual(output[0x2c7:0x2cd],b'Maker\0')
        self.assertEqual(output[0x2cd:0x307],initial[0x2cd:0x307])
        self.assertEqual(output[0x399:0x39d],b'pic\0')
        self.assertEqual(output[0x39d:],initial[0x39d:])

    def test_missing_lookup_differs_from_present_empty_fields(self):
        initial = b'Z'*1596
        self.assertEqual(apply_owned_model_brand(initial,None,text_encoding='cp1252'),initial)
        output = apply_owned_model_brand(initial,dict(Brand=None,PicName=None),text_encoding='cp1252')
        for offset in (0x2c7,0x399):
            self.assertEqual(output[offset:offset+2],b'\0Z')

    def test_cache_prefix_limits_and_embedded_null_rejection(self):
        output = apply_owned_model_brand(bytes(1596),dict(Brand='b'*90,PicName='p'*20),text_encoding='cp1252')
        self.assertEqual(output[0x2c7:0x307],b'b'*63+b'\0')
        self.assertEqual(output[0x399:0x3a2],b'p'*8+b'\0')
        with self.assertRaises(ValueError):
            apply_owned_model_brand(bytes(1596),dict(Brand='bad\0label',PicName='pic'),text_encoding='cp1252')
