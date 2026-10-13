import struct
import unittest
from client.owned_parts import OwnedPart, OwnedPartCache, OwnedInstanceCache


class OwnedPartTests(unittest.TestCase):
    def row(self, identifier=42, damage=17):
        return dict(PartID=identifier,BrandedPartID=123,PercentDamage=damage,
                    ItemWear=9,ParentPartID=0,RepairCost=500,ScrapValue=200)

    def test_instance_state_survives_shared_branded_identity(self):
        cache = OwnedPartCache((self.row(42,17),self.row(43,60)))
        slots = cache.seed_car_pairs((struct.pack('<II',43,123),struct.pack('<II',42,123),bytes(8)))
        self.assertEqual(len(slots[0]),1596)
        self.assertEqual(struct.unpack_from('<I',slots[0],0x5f8)[0],43)
        self.assertEqual(struct.unpack_from('<I',slots[0],0x1e3)[0],123)
        self.assertEqual(struct.unpack_from('<i',slots[0],0x610)[0],60)
        self.assertEqual(struct.unpack_from('<i',slots[1],0x610)[0],17)
        self.assertEqual(slots[2],bytes(1596))
        self.assertEqual(slots[0][:0x1e3],bytes(0x1e3))

    def test_missing_duplicate_and_invalid_instance_data_fail(self):
        with self.assertRaises(ValueError):
            OwnedPartCache((self.row(),self.row()))
        cache = OwnedPartCache((self.row(),))
        with self.assertRaises(ValueError):
            cache.seed_car_pairs((struct.pack('<II',99,123),))
        with self.assertRaises(ValueError):
            cache.seed_car_pairs((b'short',))
        self.assertEqual(OwnedPart.from_row(self.row(damage=None)).percent_damage,0)

    def test_car_list_cache_updates_owner_brand_and_explicit_zero_fields(self):
        row = self.row()
        row.update(OwnerID=7,ParentPartID=99,AttachmentPointID=10,PartName='retained')
        cache = OwnedInstanceCache((row,))
        cache.apply_persona_car_pairs(123,(struct.pack('<II',42,456),
            struct.pack('<II',43,789),bytes(8),struct.pack('<II',42,987)))
        updated = cache.row(42)
        self.assertEqual((updated['OwnerID'],updated['BrandedPartID']),(123,987))
        self.assertEqual(updated['PartName'],'retained')
        self.assertIsNone(updated['ParentPartID'])
        for field in ('AttachmentPointID','PercentDamage','ItemWear','RepairCost','ScrapValue'):
            self.assertEqual(updated[field],0)
        copied = cache.row(42)
        copied['PercentDamage'] = 99
        self.assertEqual(cache.row(42)['PercentDamage'],0)
        seeds = cache.part_cache().seed_car_pairs((struct.pack('<II',42,987),))
        self.assertEqual(struct.unpack_from('<I',seeds[0],0x1e3)[0],987)
        self.assertEqual(struct.unpack_from('<I',seeds[0],0x60c)[0],0)
        with self.assertRaises(ValueError):
            cache.apply_persona_car_pairs(123,(struct.pack('<II',44,1),b'bad'))
        with self.assertRaises(ValueError):
            cache.row(44)
