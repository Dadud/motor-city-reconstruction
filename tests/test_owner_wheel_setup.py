import struct
import unittest
from client.owner_wheel_setup import initialize_owner_wheels, OWNER_SIZE


class OwnerWheelSetupTests(unittest.TestCase):
    def fixture(self):
        owner=bytearray(OWNER_SIZE); config=bytearray(0x820)
        for image,offset,value in ((owner,0x18ec,.35),(owner,0x18f0,.35),
                (config,0x144,200.),(config,0x124,200.),(config,0x228,280.)):
            struct.pack_into('<f',image,offset,value)
        return owner,config

    def test_zero_flags_use_original_rear_pair_and_preserve_inputs(self):
        owner,config=self.fixture(); before=bytes(owner),bytes(config)
        result=initialize_owner_wheels(owner,config,assembly_finalized=True)
        self.assertEqual([result[o] for o in (0x6c1,0x7cd,0x8d9,0x9e5)], [0,0,1,1])
        self.assertEqual((bytes(owner),bytes(config)),before)

    def test_rear_width_ratio_uses_front_template(self):
        owner,config=self.fixture()
        first=initialize_owner_wheels(owner,config,assembly_finalized=True)
        struct.pack_into('<f',config,0x248,1000.)
        second=initialize_owner_wheels(owner,config,assembly_finalized=True)
        self.assertEqual(first,second)
        self.assertAlmostEqual(struct.unpack_from('<f',first,0x8cc+0x40)[0],1.4,places=6)

    def test_incomplete_assembly_is_rejected(self):
        owner,config=self.fixture()
        with self.assertRaises(ValueError): initialize_owner_wheels(owner,config,assembly_finalized=False)


if __name__=='__main__': unittest.main()
