import struct
import unittest
from dataclasses import replace
from client.owned_parts import OwnedEngineFamily


class OwnedFamilyTests(unittest.TestCase):
    def slot(self):
        slot = bytearray(b'Z'*1596)
        struct.pack_into('<i',slot,0x203,10)
        return bytes(slot)

    def test_family_query_and_brand_cache_are_distinct_sources(self):
        family = OwnedEngineFamily(10,7,'Query Brand','Family Name','Short')
        initial = self.slot()
        output = family.apply(initial,text_encoding='cp1252',brand_cache_name='Cached Brand')
        for offset,capacity,text in ((0x2c7,63,b'Cached Brand'),(0x3a2,63,b'Query Brand'),
                (0x3e2,25,b'Family Name'),(0x3fc,7,b'Short')):
            self.assertEqual(output[offset:offset+capacity],text.ljust(capacity,b'\0'))
            self.assertEqual(output[offset+capacity],ord('Z'))
        self.assertEqual(output[0x404:],initial[0x404:])
        self.assertEqual(output[:0x2c7],initial[:0x2c7])

    def test_missing_brand_cache_clears_only_first_byte(self):
        family = OwnedEngineFamily(10,7,None,None,None)
        output = family.apply(self.slot(),text_encoding='cp1252',brand_cache_name=None)
        self.assertEqual(output[0x2c7:0x306],b'\0'+b'Z'*62)
        self.assertEqual(output[0x3e2:0x3fb],bytes(25))
        empty = family.apply(self.slot(),text_encoding='cp1252',brand_cache_name='')
        self.assertEqual(empty[0x2c7:0x306],bytes(63))

    def test_identity_and_query_buffer_bounds_are_enforced(self):
        family = OwnedEngineFamily(10,7,'Brand','Family','Short')
        for field,value in (('family_id',11),('family_id',-1),('name','x'*26),
                            ('short_name','x'*8),('brand_name','x'*64)):
            with self.assertRaises(ValueError):
                replace(family,**{field:value}).apply(self.slot(),text_encoding='cp1252',brand_cache_name='Brand')
