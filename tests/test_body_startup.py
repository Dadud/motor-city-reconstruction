import struct
import unittest
from client.body_geometry import body_samples,customize_body_samples
from client.body_startup import prepare_startup_body
from tools.body_startup_oracle import startup_cases


class BodyStartupTests(unittest.TestCase):
    def test_original_no_op_shapes_and_changed_samples(self):
        points=body_samples(0,(1.,.5,2.))
        self.assertEqual(customize_body_samples(0,points),points)
        self.assertEqual(customize_body_samples(3,points),points)
        custom=customize_body_samples(1,points)
        self.assertEqual(custom[4][1],.25)
        self.assertEqual(custom[7][1],struct.unpack('<f',struct.pack('<f',.15))[0])
        self.assertEqual(custom[8],points[8])

    def test_connected_phase_preserves_snapshot_and_prior_lever(self):
        owner,config,extents,identity=next(startup_cases())
        out=prepare_startup_body(owner,config,extents,identity,assembly_finalized=True)
        self.assertEqual(out[0x418:],owner[0x418:])
        self.assertNotEqual(out[0xe0:0x1e8],out[0x1e8:0x2f0])
        self.assertEqual(out[0x18b8:0x18bc],owner[0x18b8:0x18bc])
        self.assertEqual(out[0x308:0x30c],config[:4])

    def test_requires_final_assembly_and_valid_selector(self):
        owner,config,extents,identity=next(startup_cases())
        with self.assertRaises(ValueError):prepare_startup_body(owner,config,extents,identity,assembly_finalized=False)
        config=bytearray(config);struct.pack_into('<i',config,0x48,8)
        with self.assertRaises(ValueError):prepare_startup_body(owner,config,extents,identity,assembly_finalized=True)


if __name__=='__main__':unittest.main()
