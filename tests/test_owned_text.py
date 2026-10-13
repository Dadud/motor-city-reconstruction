import unittest
from dataclasses import replace
from client.owned_parts import OwnedPartMetadata


class OwnedTextTests(unittest.TestCase):
    def metadata(self):
        return OwnedPartMetadata(20001,200,500,1000,1955,3,0,7,
                                 'Body','Coupe','Short','Details','coupe')

    def test_copy_regions_preserve_trailing_and_instance_bytes(self):
        initial = b'Z'*1596
        output = self.metadata().apply_text_fields(initial,text_encoding='cp1252')
        for offset,text in ((0x307,b'Coupe\0'),(0x287,b'Short\0'),
                            (0x20,b'Details\0'),(0x387,b'coupe\0')):
            self.assertEqual(output[offset:offset+len(text)],text)
            self.assertEqual(output[offset+len(text)],ord('Z'))
        self.assertEqual(output[0x347:0x387],b'Body'+bytes(60))
        self.assertEqual(output[0x390],0)
        self.assertEqual(output[0x5f8:],initial[0x5f8:])

    def test_null_text_copies_one_zero_byte_and_type_name_pads(self):
        metadata = replace(self.metadata(),part_type_name=None,model_name=None,
                           short_model_name=None,extra_info=None,part_filename=None)
        output = metadata.apply_text_fields(b'Z'*1596,text_encoding='cp1252')
        for offset in (0x20,0x287,0x307,0x387):
            self.assertEqual(output[offset:offset+2],b'\0Z')
        self.assertEqual(output[0x347:0x387],bytes(64))

    def test_byte_limits_and_explicit_narrow_encoding(self):
        metadata = replace(self.metadata(),part_type_name='t'*80,model_name='m'*63,
                           short_model_name='s'*63,extra_info='e'*351,part_filename='f'*8)
        output = metadata.apply_text_fields(bytes(1596),text_encoding='cp1252')
        self.assertEqual(output[0x347:0x387],b't'*63+b'\0')
        self.assertEqual(output[0x387:0x390],b'f'*8+b'\0')
        accented = replace(metadata,model_name='Caf\u00e9')
        self.assertEqual(accented.apply_text_fields(bytes(1596),text_encoding='cp1252')[0x307:0x30c],b'Caf\xe9\0')
        with self.assertRaises(UnicodeEncodeError):
            accented.apply_text_fields(bytes(1596),text_encoding='ascii')

    def test_rejects_unbounded_native_inputs(self):
        for field,capacity in (('model_name',64),('short_model_name',64),
                               ('extra_info',352),('part_filename',9)):
            with self.assertRaises(ValueError):
                replace(self.metadata(),**{field:'x'*capacity}).apply_text_fields(bytes(1596),text_encoding='cp1252')
        with self.assertRaises(ValueError):
            replace(self.metadata(),model_name='embedded\0null').apply_text_fields(bytes(1596),text_encoding='cp1252')
