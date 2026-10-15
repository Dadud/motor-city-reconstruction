import struct
import unittest
from client.mechanical_parts import expand_mechanical_parts,transfer_mechanical_physics
from client.tire_response import f32


class MechanicalPartsTests(unittest.TestCase):
    def slot(self,attachment=10,paired=1,branded=100):
        out=bytearray(1596)
        struct.pack_into('<I',out,0x1e3,branded)
        struct.pack_into('<i',out,0x10,paired)
        struct.pack_into('<i',out,0x61c,attachment)
        return out

    def test_pairing_preserves_source_indices_and_does_not_guess_from_type(self):
        sources=(bytes(self.slot(10)),bytes(self.slot(11,branded=0)),
            bytes(self.slot(11)),bytes(self.slot(0)),bytes(self.slot(10,paired=0)))
        out=expand_mechanical_parts(sources)
        self.assertEqual([(p.source_index,p.attachment) for p in out],
            [(0,1),(0,2),(2,3),(2,4),(3,5),(3,6),(4,10)])
        self.assertEqual(sources[0],bytes(self.slot(10)))
        self.assertEqual(expand_mechanical_parts(()),())

    def test_unsigned_damage_wear_and_numeric_count_are_not_sanitized(self):
        slot=self.slot();struct.pack_into('<I',slot,0x610,0xffffffff)
        struct.pack_into('<I',slot,0x614,0x80000001)
        struct.pack_into('<i',slot,0x1ef,-27)
        struct.pack_into('<I',slot,0x420,0)
        struct.pack_into('<f',slot,0x42c,123.5)
        out=transfer_mechanical_physics(bytes(slot),1)
        self.assertEqual(struct.unpack_from('<f',out,0x104)[0],f32(0xffffffff*f32(.01)))
        self.assertEqual(struct.unpack_from('<f',out,0x108)[0],f32(0x80000001*1000.))
        self.assertEqual(struct.unpack_from('<f',out,0x20)[0],-27000.)
        self.assertEqual(struct.unpack_from('<f',out,0x3c)[0],123.5)
        self.assertEqual(out[0x338:0x974],slot)

    def test_text_count_copies_a_prefix_and_preserves_unwritten_bytes(self):
        slot=self.slot();struct.pack_into('<I',slot,0x424,2)
        slot[0x4f4:0x4f8]=b'one\0';slot[0x534:0x538]=b'tri\0'
        out=transfer_mechanical_physics(bytes(slot),1,initial_image=b'\xa5'*0x984)
        self.assertEqual(out[0x120:0x124],b'one\0')
        self.assertEqual(out[0x140],0)
        self.assertEqual(out[0x141:0x144],b'\xa5'*3)
        self.assertEqual(out[0x160:0x164],b'\xa5'*4)
        self.assertEqual(out[0x220:0x224],b'\xa5'*4)

    def test_malformed_input_is_bounded(self):
        with self.assertRaises(ValueError):transfer_mechanical_physics(b'',1)
        with self.assertRaises(ValueError):transfer_mechanical_physics(bytes(self.slot()),True)
        slot=self.slot();struct.pack_into('<I',slot,0x424,1)
        slot[0x4f4:0x514]=b'x'*32
        with self.assertRaisesRegex(ValueError,'terminator'):
            transfer_mechanical_physics(bytes(slot),1)
