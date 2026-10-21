import struct
import unittest
from client.mechanical_parts import (expand_mechanical_parts,
    create_mechanical_slot_buffer, transfer_mechanical_physics,
    transfer_mechanical_presentation)
from client.tire_response import f32


class MechanicalPartsTests(unittest.TestCase):
    def test_slot_buffer_allocation_is_zeroed_and_has_two_records_per_slot(self):
        calls=[]
        def allocate(tag,size,pool):
            calls.append((tag,size,pool))
            return bytearray([0xa5])*size
        result=create_mechanical_slot_buffer(3,allocate,pool=7)
        self.assertEqual(calls,[(b'PARTS',3*0x1308,7)])
        self.assertEqual(len(result),3*0x1308)
        self.assertFalse(any(result))
        self.assertIsNone(create_mechanical_slot_buffer(0,allocate,pool=7))
        self.assertEqual(len(calls),1)

    def test_slot_buffer_preserves_allocation_failure_and_bounds_inputs(self):
        self.assertIsNone(create_mechanical_slot_buffer(2,lambda *_:None,pool=0))
        for count in (-1,10001,True):
            with self.subTest(count=count),self.assertRaises(ValueError):
                create_mechanical_slot_buffer(count,lambda *_:bytearray(),pool=0)
        with self.assertRaises(ValueError):
            create_mechanical_slot_buffer(1,lambda *_:bytearray(4),pool=0)

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

    def test_presentation_builds_literal_and_prefixed_model_paths(self):
        slot=self.slot();slot[0x387:0x38f]=b'.factory';slot[0x390:0x394]=b'Ford'
        slot[0x2c7:0x2ca]=b'EA\0'
        display_name=b'Generic Part\0'
        slot[0x307:0x307+len(display_name)]=display_name
        initial=b'\xa5'*0x984
        out=transfer_mechanical_presentation(bytes(slot),model_prefix='data/models/',
                                             initial_image=initial)
        self.assertEqual(out[0x220:0x229],b'.factory\0')
        self.assertEqual(out[0x22c:0x235],b'.factory\0')
        self.assertEqual(out[0x32c:0x335],b'Ford\0\0\0\0\0')
        self.assertEqual(out[0x53f:0x53f+len(b'EA Generic Part\0')],
                         b'EA Generic Part\0')
        self.assertEqual(out[0x600:],initial[0x600:])

        slot[0x387:0x390]=b'32ford\0\0\0'
        out=transfer_mechanical_presentation(bytes(slot),model_prefix='data/models/',
                                             initial_image=initial)
        self.assertEqual(out[0x220:0x229],b'32ford\0\0\0')
        path=b'data/models/32ford.viv\0'
        self.assertEqual(out[0x22c:0x22c+len(path)],path)

    def test_presentation_truncates_display_at_original_64_byte_buffer(self):
        slot=self.slot();slot[0x2c7:0x307]=b'A'*63+b'\0'
        slot[0x307:0x348]=b'B'*64+b'\0'
        out=transfer_mechanical_presentation(bytes(slot),model_prefix=b'',
                                             initial_image=b'\xa5'*0x984)
        self.assertEqual(out[0x53f:0x57f],b'A'*63+b'\0')

    def test_presentation_rejects_unterminated_fields_and_invalid_prefix(self):
        slot=self.slot();slot[0x387:0x390]=b'123456789'
        with self.assertRaisesRegex(ValueError,'model-source'):
            transfer_mechanical_presentation(bytes(slot),model_prefix='',
                                             initial_image=b'\0'*0x984)
        slot=self.slot()
        with self.assertRaisesRegex(ValueError,'display brand'):
            transfer_mechanical_presentation(bytes(slot[:0x2c7])+b'A'*64+bytes(0x63c-0x307),
                                             model_prefix='',initial_image=b'\0'*0x984)
        with self.assertRaisesRegex(ValueError,'NUL-free'):
            transfer_mechanical_presentation(bytes(slot),model_prefix=b'x\0',
                                             initial_image=b'\0'*0x984)

    def test_malformed_input_is_bounded(self):
        with self.assertRaises(ValueError):transfer_mechanical_physics(b'',1)
        with self.assertRaises(ValueError):transfer_mechanical_physics(bytes(self.slot()),True)
        slot=self.slot();struct.pack_into('<I',slot,0x424,1)
        slot[0x4f4:0x514]=b'x'*32
        with self.assertRaisesRegex(ValueError,'terminator'):
            transfer_mechanical_physics(bytes(slot),1)
