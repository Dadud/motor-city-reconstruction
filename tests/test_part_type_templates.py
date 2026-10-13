import struct
import unittest
from client.part_type_templates import encode_part_type_template, apply_part_type_template


class PartTypeTemplateTests(unittest.TestCase):
    def row(self):
        return dict(AbstractPartTypeID=101,ParentAbstractPartTypeID=20001,DependsOn=160001,
            ModifiedRule=3,PartPaired=1,BlockFamilyCompatibility=2,GarageCategory=4,
            RepairCostModifier=0.125,ScrapValueModifier=0.375,EAPT='Type',EUT='Units',
            PartFilename='partfile',SchematicPicname1='picture1',SchematicPicname2='picture2')

    def test_template_distinguishes_pairing_compatibility_and_category(self):
        template = encode_part_type_template(self.row(),text_encoding='cp1252')
        self.assertEqual(struct.unpack_from('<8i',template),(101,20001,160001,1,1,2,4,3))
        self.assertEqual(struct.unpack_from('<ff',template,0x1db),(0.125,0.375))
        self.assertEqual(struct.unpack_from('<ii',template,0x600),(-1,-1))
        self.assertEqual(template[0x1c0:0x1c9],b'partfile\0')
        row = dict(self.row(),AbstractPartTypeID=20001)
        self.assertEqual(struct.unpack_from('<I',encode_part_type_template(row,text_encoding='cp1252'),0xc)[0],0)

    def test_copy_uses_template_asset_names_and_preserves_instance_state(self):
        template = encode_part_type_template(self.row(),text_encoding='cp1252')
        initial = bytearray(b'Z'*1596)
        struct.pack_into('<I',initial,0,101)
        output = apply_part_type_template(bytes(initial),template)
        self.assertEqual(output[0x1c0:0x1db],b'partfile\0picture1\0picture2\0')
        self.assertEqual(output[0x1db:0x1e3],template[0x1db:0x1e3])
        self.assertEqual(output[0x1e3:],initial[0x1e3:])
        self.assertEqual(output[0x14:0x18],initial[0x14:0x18])
        with self.assertRaises(ValueError):
            apply_part_type_template(bytes(1596),template)

    def test_nulls_and_byte_truncation_match_cache_initialization(self):
        row = dict(self.row(),ParentAbstractPartTypeID=None,DependsOn=None,ModifiedRule=None,
                   PartPaired=None,EAPT='t'*100,EUT='u'*500,PartFilename=None)
        template = encode_part_type_template(row,text_encoding='cp1252',parent_index=0,depends_index=0)
        self.assertEqual(template[0x180:0x1c0],b't'*63+b'\0')
        self.assertEqual(template[0x20:0x180],b'u'*351+b'\0')
        self.assertEqual(template[0x1c0:0x1c9],bytes(9))
        self.assertEqual(struct.unpack_from('<ii',template,4),(0,0))
        self.assertEqual(struct.unpack_from('<ii',template,0x600),(0,0))

    def test_invalid_numbers_and_text_fail(self):
        for field,value in (('RepairCostModifier',float('nan')),('ScrapValueModifier',1e100),
                            ('PartPaired',True),('EAPT','embedded\0null')):
            with self.assertRaises(ValueError):
                encode_part_type_template(dict(self.row(),**{field:value}),text_encoding='cp1252')
