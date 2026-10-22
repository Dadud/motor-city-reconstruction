import struct
import unittest
from client.body_constructor import construct_body
from client.body_geometry import body_samples


class BodyConstructorTests(unittest.TestCase):
    def test_preserves_derived_owner_and_copies_samples(self):
        owner=bytes([0xa5])*0x2000
        result=construct_body(owner,17,0,(1.,.5,2.),0,6)
        self.assertEqual(result[0x418:],owner[0x418:])
        self.assertEqual(result[0xe0:0x1e8],result[0x1e8:0x2f0])
        self.assertEqual(struct.unpack_from('<f',result,0x50)[0],1000.)
        self.assertEqual(struct.unpack_from('<f',result,0x74)[0],8.)

    def test_geometry_faces_precede_rounding(self):
        points=body_samples(3,(1.,.5,2.))
        self.assertEqual(points[8],(0.,0.,2.))
        self.assertAlmostEqual(points[0][0],-.707,places=6)
        self.assertEqual(points[0][1],-.5)
        self.assertEqual(body_samples(1,(1.,.5,2.))[4],(0.,.5,0.))

    def test_sphere_uses_maximum_extent(self):
        owner=bytes(0x2000)
        result=construct_body(owner,0,1000,(1.,.5,2.),4,0)
        self.assertEqual(struct.unpack_from('<3f',result,0xcc),(2.,2.,2.))

    def test_zero_extent_preserves_ieee_infinities_from_native_constructor(self):
        result=construct_body(bytes(0x2000),0xfffffffd,25.,(0.,3.,0.),0,2)
        self.assertEqual(struct.unpack_from('<3f',result,0xcc),(0.,3.,0.))
        self.assertEqual(struct.unpack_from('<3f',result,0x2f0),(75.,0.,75.))
        self.assertEqual(struct.unpack_from('<f',result,0x70)[0],float('inf'))
        self.assertEqual(struct.unpack_from('<3f',result,0x2fc)[1],float('inf'))

    def test_rejects_unverified_domains(self):
        for mass,extent,shape in ((-1.,(1.,1.,1.),0),(1.,(1.,1.,1.),5)):
            with self.assertRaises(ValueError): construct_body(bytes(0x2000),0,mass,extent,shape,0)


if __name__=='__main__': unittest.main()
