import struct
import unittest

from client.contact_force import contact_forces_step, contact_response


class ContactForceTests(unittest.TestCase):
    def make_record(self):
        record=bytearray(0x4f8)
        struct.pack_into('<f',record,0x54,1)
        struct.pack_into('<9f',record,0x78,1,0,0,0,1,0,0,0,1)
        struct.pack_into('<9f',record,0x9c,1,0,0,0,1,0,0,0,1)
        struct.pack_into('<3f',record,0x2fc,1,1,1)
        return record

    def test_contact_response_approaching_and_separating(self):
        record=self.make_record()
        linear,angular=contact_response(record,(-2,0,0),(1,2,0),(1,0,0))
        self.assertEqual(linear,(-2,0,0))
        self.assertEqual(angular,(0,0,4))
        linear,angular=contact_response(record,(2,0,0),(1,2,0),(1,0,0))
        self.assertEqual(linear,(0,0,0))
        self.assertEqual(angular,(0,0,-4))

    def test_six_contact_accumulation_updates_linear_and_angular_velocity(self):
        record=self.make_record()
        record[4]=1
        struct.pack_into('<h',record,0x3bc,1)
        struct.pack_into('<3f',record,0x14,1,0,0)
        for offset in (0x248,0x254,0x260,0x26c,0x278,0x284):
            struct.pack_into('<3f',record,offset,1,0,0)
        calls=[]
        def response(image,force,point,normal):
            calls.append((point,normal))
            return (1,0,0),(0,1,0)
        contact_forces_step(record,response)
        self.assertEqual(len(calls),6)
        self.assertEqual(struct.unpack_from('<f',record,0x14)[0],1.1875)
        self.assertAlmostEqual(struct.unpack_from('<f',record,0x3c)[0],
                               6*0.004973592,places=7)

    def test_counter_gate_and_invalid_response(self):
        record=self.make_record()
        calls=[]
        contact_forces_step(record,lambda *_:calls.append(1))
        self.assertEqual(calls,[])
        with self.assertRaisesRegex(ValueError,'per-contact response'):
            contact_forces_step(record,None)


if __name__=='__main__':unittest.main()
