import struct
import unittest
from client.mcots_data_records import MCOTSFixed186Record
from client.owned_valuation import PartValuationRates, calculate_owned_valuation, apply_owned_valuation


class OwnedValuationTests(unittest.TestCase):
    def slot(self, *, identifier=160001,price=500,maximum=1000,damage=20,wear=250,body_value=0):
        output = bytearray(1596)
        struct.pack_into('<I',output,0,identifier)
        struct.pack_into('<I',output,0x1e3,123)
        struct.pack_into('<ii',output,0x1eb,price,maximum)
        struct.pack_into('<f',output,0x454,body_value)
        struct.pack_into('<I',output,0x5f8,42)
        struct.pack_into('<ii',output,0x610,damage,wear)
        struct.pack_into('<ii',output,0x62c,999,888)
        return bytes(output)

    def test_rates_come_from_server_reply_or_explicit_absent_record(self):
        record = bytearray(118)
        struct.pack_into('<H',record,0,0x186)
        struct.pack_into('<dd',record,0x1e,0.2,0.65)
        self.assertEqual(PartValuationRates.from_reply(MCOTSFixed186Record(bytes(record))),PartValuationRates(0.2,0.65))
        self.assertEqual(PartValuationRates.from_reply(None),PartValuationRates(0.1,0.75))
        struct.pack_into('<dd',record,0x1e,0.0,0.0)
        self.assertEqual(PartValuationRates.from_reply(MCOTSFixed186Record(bytes(record))),PartValuationRates(0.0,0.0))
        with self.assertRaises(ValueError):
            PartValuationRates(float('nan'),0.75)

    def test_condition_and_costs_use_original_arithmetic(self):
        result = calculate_owned_valuation(self.slot(),PartValuationRates(0.1,0.75))
        self.assertEqual((result.repair_cost,result.scrap_value,result.wear_condition),(10,271,0.75))
        output = apply_owned_valuation(self.slot(),PartValuationRates(0.1,0.75))
        self.assertEqual(output[:0x62c],self.slot()[:0x62c])
        self.assertEqual(struct.unpack_from('<ii',output,0x62c),(10,271))
        self.assertEqual(output[0x634:],self.slot()[0x634:])

    def test_float32_percentage_changes_half_unit_rounding(self):
        result = calculate_owned_valuation(self.slot(price=25,damage=100,wear=0),PartValuationRates(0.1,0.75))
        self.assertEqual(result.repair_cost,2)

    def test_zero_wear_limit_and_no_damage_branches(self):
        result = calculate_owned_valuation(self.slot(maximum=0,damage=0,wear=500),PartValuationRates(0.1,0.75))
        self.assertEqual((result.repair_cost,result.scrap_value,result.wear_condition),(0,375,1.0))
        result = calculate_owned_valuation(self.slot(price=1,damage=1,wear=2000),PartValuationRates(0.1,0.75))
        self.assertEqual((result.repair_cost,result.scrap_value),(1,0))

    def test_body_value_eleven_bonus_has_exact_type_range(self):
        rates = PartValuationRates(0.1,0.75)
        for identifier,expected in ((20000,271),(20001,363),(20999,363),(21000,271)):
            result = calculate_owned_valuation(self.slot(identifier=identifier,body_value=123.25),rates)
            self.assertEqual(result.scrap_value,expected)

    def test_empty_identity_preserves_cached_values(self):
        slot = bytearray(self.slot())
        struct.pack_into('<I',slot,0x5f8,0)
        rates = PartValuationRates(0.1,0.75)
        self.assertIsNone(calculate_owned_valuation(bytes(slot),rates))
        self.assertEqual(apply_owned_valuation(bytes(slot),rates),bytes(slot))
