import struct
import unittest
from client.owned_physics import encode_owned_physics, apply_owned_physics


class OwnedPhysicsTests(unittest.TestCase):
    def row(self):
        row = dict(PartTypeID=200,Ordinal=2,StatusID=3,DutyRating=4,
                   MaxItemWear=10000,Mass=13.125)
        row.update({f'Val{i}': None for i in range(1,51)})
        row.update({f'TextVal{i}': None for i in range(1,9)})
        return row

    def test_null_stops_values_but_text_fields_are_independent(self):
        row = self.row()
        row.update(Val1=1.25,Val3=99,TextVal2='',TextVal4='x'*40)
        record = encode_owned_physics(row,text_encoding='cp1252')
        self.assertEqual(len(record),496)
        self.assertEqual(record[:8],bytes(8))
        self.assertEqual(struct.unpack_from('<II',record,28),(1,2))
        self.assertEqual(struct.unpack_from('<f',record,40)[0],1.25)
        self.assertEqual(record[44:240],bytes(196))
        self.assertEqual(record[336:368],b'x'*32)

    def test_checksum_excludes_labels_but_includes_part_type_and_values(self):
        row = self.row()
        baseline = encode_owned_physics(row,text_encoding='cp1252')[36:40]
        row.update(Ordinal=5,StatusID=7,TextVal1='label')
        self.assertEqual(encode_owned_physics(row,text_encoding='cp1252')[36:40],baseline)
        row['PartTypeID'] += 1
        self.assertNotEqual(encode_owned_physics(row,text_encoding='cp1252')[36:40],baseline)

    def test_placement_preserves_instance_state_and_overrides_wear_limit(self):
        slot = bytearray(b'Z'*1596)
        struct.pack_into('<i',slot,0x1e7,200)
        output = apply_owned_physics(bytes(slot),self.row(),text_encoding='cp1252')
        self.assertEqual(output[0x5f8:],slot[0x5f8:])
        self.assertEqual(output[0x404:0x5f4],encode_owned_physics(self.row(),text_encoding='cp1252'))
        self.assertEqual(struct.unpack_from('<i',output,0x1ef)[0],10000)
        with self.assertRaises(ValueError):
            apply_owned_physics(bytes(1596),self.row(),text_encoding='cp1252')

    def test_invalid_data_is_rejected(self):
        for value in (float('inf'),float('nan'),True,1e100):
            row = self.row()
            row['Val1'] = value
            with self.assertRaises(ValueError):
                encode_owned_physics(row,text_encoding='cp1252')
        row = self.row()
        del row['Val50']
        with self.assertRaises(ValueError):
            encode_owned_physics(row,text_encoding='cp1252')
