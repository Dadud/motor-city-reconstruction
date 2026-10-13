import struct
import unittest
from client.owned_parts import OwnedPart, OwnedPartCache


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
        with self.assertRaises(ValueError):
            OwnedPart.from_row(self.row(damage=None)).native_seed()
