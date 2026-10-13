import struct
import unittest
from client.mcots_data_records import (MCOTSList145Record, MCOTSList143Record,
    MCOTSList16CRecord, MCOTSFixed186Record, first_145_identifier_for_value)


class DataRecordsTests(unittest.TestCase):
    def record(self, identifier=42, value=7, text=b'name', flag=255, reference=123):
        raw = bytearray(569)
        struct.pack_into('<II',raw,0,identifier,value)
        raw[12:12+len(text)] = text
        raw[44] = flag
        struct.pack_into('<I',raw,0x137,reference)
        return MCOTSList145Record(bytes(raw))

    def test_selection_predicate_and_first_match_have_distinct_behavior(self):
        record = self.record()
        self.assertTrue(record.eligible(True))
        self.assertFalse(record.eligible(False))
        self.assertEqual((record.identifier,record.value_04,record.text_window_0c,
                          record.flag_2c,record.reference_137),(42,7,b'name',255,123))
        for invalid in (self.record(identifier=0),self.record(value=0),
                        self.record(text=b''),self.record(flag=0),self.record(reference=0)):
            self.assertFalse(invalid.eligible(True))
        self.assertTrue(self.record(value=14,text=b'').eligible(True))
        records = (self.record(identifier=0),self.record(identifier=99))
        self.assertEqual(first_145_identifier_for_value(records,7),0)
        self.assertEqual(first_145_identifier_for_value(records,8),0)

    def test_unaligned_numeric_fields_and_unknown_bodies(self):
        raw = bytearray(118)
        struct.pack_into('<H3I',raw,0,0x186,1,0xffffffff,3)
        struct.pack_into('<dd',raw,0x1e,0.1,0.75)
        fixed = MCOTSFixed186Record(bytes(raw))
        self.assertEqual(fixed.values_02,(1,0xffffffff,3))
        self.assertEqual((fixed.double_1e,fixed.double_26),(0.1,0.75))
        pair = MCOTSList143Record(struct.pack('<II',99,7))
        self.assertEqual((pair.value_00,pair.value_04),(99,7))
        opaque = MCOTSList16CRecord(struct.pack('<I',99)+b'x'*512)
        self.assertEqual((opaque.identifier,opaque.body),(99,b'x'*512))
        for cls, size in ((MCOTSList145Record,569),(MCOTSList143Record,8),
                          (MCOTSList16CRecord,516),(MCOTSFixed186Record,118)):
            with self.assertRaises(ValueError):
                cls(bytes(size-1))
