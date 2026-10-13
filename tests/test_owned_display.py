import struct
import unittest
from client.part_type_templates import apply_owned_display_names


class OwnedDisplayTests(unittest.TestCase):
    def slots(self,identifier=20001,year=1955,brand=b'Maker',model=b'Model'):
        slot = bytearray(b'Z'*1596)
        struct.pack_into('<i',slot,0,identifier)
        struct.pack_into('<i',slot,0x1fb,year)
        slot[0x2c7:0x307] = (brand+b'\0').ljust(64,b'\0')
        slot[0x307:0x347] = (model+b'\0').ljust(64,b'\0')
        template = bytearray(1596)
        struct.pack_into('<i',template,0,identifier)
        template[0x180:0x1c0] = b'Category\0'.ljust(64,b'\0')
        return bytes(slot),bytes(template)

    def test_mode_two_preserves_short_name_and_unwritten_tails(self):
        slot,template = self.slots()
        output = apply_owned_display_names(slot,template)
        self.assertEqual(output[0x207:0x213],b'Maker Model\0')
        self.assertEqual(output[0x213:0x287],slot[0x213:0x287])
        self.assertEqual(output[0x287:0x2c7],slot[0x287:0x2c7])
        self.assertEqual(output[0x180:0x189],b'Category\0')
        self.assertEqual(output[0x189:0x207],slot[0x189:0x207])

    def test_alternate_mode_updates_short_name_and_special_type_display(self):
        for identifier,expected in ((20001,b'Maker Model'),(1001,b'Model')):
            slot,template = self.slots(identifier)
            output = apply_owned_display_names(slot,template,mode=1)
            self.assertEqual(output[0x207:0x287].split(b'\0',1)[0],expected)
            self.assertEqual(output[0x287:0x28d],b'Model\0')

    def test_vehicle_year_prefix_in_both_modes(self):
        for mode,year,expected in ((2,1955,b"'55 Maker Model"),(1,1899,b"'-1 Maker Model"),
                                   (2,2005,b"'105 Maker Model")):
            slot,template = self.slots(101,year)
            output = apply_owned_display_names(slot,template,mode=mode)
            self.assertEqual(output[0x207:0x287].split(b'\0',1)[0],expected)

    def test_empty_brand_preserves_original_separator(self):
        slot,template = self.slots(brand=b'')
        output = apply_owned_display_names(slot,template)
        self.assertEqual(output[0x207:0x20e],b' Model\0')

    def test_rejects_unterminated_inputs_and_output_overflow(self):
        slot,template = self.slots()
        slot = bytearray(slot)
        slot[0x307:0x347] = b'x'*64
        with self.assertRaises(ValueError):
            apply_owned_display_names(bytes(slot),template)
        slot,template = self.slots(101,1955,brand=b'b'*63,model=b'm'*63)
        with self.assertRaises(ValueError):
            apply_owned_display_names(slot,template)
