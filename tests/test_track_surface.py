import struct
import unittest
from client.track_surface import SurfaceHit, TrackSurface, decode_surface
from client.track_spatial import SpatialIndex, Node
from test_track_mesh import fixture as mesh_fixture


def fixture(identifier=0):
    data=mesh_fixture()
    header=56+84*2
    struct.pack_into('<I',data,header+0x660,1)
    descriptors=struct.pack('<10h',0,0,0,0,0,32767,0,0,0,0)
    start=header+0x6c4+4*16
    data[start:start]=descriptors
    data+=bytes(8)  # Two empty global object groups; UV count is zero.
    # UV indices all refer to zero, so include one coordinate.
    struct.pack_into('<I',data,52,1)
    data+=struct.pack('<f',0)
    grid=bytearray(4096*16)
    struct.pack_into('<4I',grid,(32*64+32)*16,0xdeadbeef,1,0,0)
    data+=struct.pack('<4f',-1,-1,1,1)+grid+struct.pack('<I',identifier)
    return data


class SurfaceTests(unittest.TestCase):
    def test_overlapping_height_selection_and_distance_tolerance(self):
        quad=((0,0,0),(1,0,0),(1,0,1),(0,0,1))
        upper=tuple((x,10,z) for x,_,z in quad)
        descriptor=(0,0,0,0,0,32767,0,0,0,0)
        blocks=tuple((vertices,((0,1,2,3),),(descriptor,)) for vertices in (quad,upper))
        spatial=SpatialIndex((-1,-1,2,2),(Node((0,1),()),)*4096)
        surface=TrackSurface(spatial,blocks)
        self.assertEqual(surface.lookup(0.5,0.5).block,0)
        self.assertEqual(surface.lookup(0.5,0.5,reference_height=9).block,1)
        self.assertEqual(surface.lookup(0.5,0.5,reference_height=1).block,0)
        self.assertIsNone(surface.lookup(-0.0001,0.5))
        self.assertIsNotNone(surface.lookup(-0.0001,0.5,tolerance=0.001))
        self.assertIsNone(surface.lookup(-0.01,0.5,tolerance=0.001))
        with self.assertRaisesRegex(ValueError,'tolerance'):
            surface.lookup(0,0,tolerance=-1)
        with self.assertRaisesRegex(ValueError,'reference height'):
            surface.lookup(0,0,reference_height=float('nan'))

    def test_native_diagonal_height_and_normal(self):
        hit=SurfaceHit(0,0,((0,0,0),(1,0,0),(1,1,1),(0,0,1)),())
        height,normal=hit.sample(0.25,0.25)
        self.assertEqual(height,0)
        self.assertEqual(normal,(0,1,0))
        height,normal=hit.sample(0.75,0.75)
        self.assertAlmostEqual(height,0.5)
        self.assertGreater(normal[1],0)
        self.assertAlmostEqual(sum(v*v for v in normal),1)
        vertical=SurfaceHit(0,0,((0,0,0),(0,1,0),(0,1,1),(0,0,1)),())
        with self.assertRaisesRegex(ValueError,'vertical'):
            vertical.sample(0,0.5)

    def test_leaf_reference_quad_containment_and_upward_filter(self):
        surface=decode_surface(fixture())
        hit=surface.lookup(0.01,0.01)
        self.assertIsNotNone(hit)
        self.assertEqual((hit.block,hit.descriptor),(0,0))
        self.assertEqual(surface.lookup(-0.01,-0.01),None)
        data=fixture()
        struct.pack_into('<h',data,56+84*2+0x6c4+4*16+10,-1)
        surface=decode_surface(data)
        self.assertIsNone(surface.lookup(0.01,0.01))
        self.assertIsNotNone(surface.lookup(0.01,0.01,upward_only=False))

    def test_invalid_block_descriptor_and_polygon_references(self):
        for identifier in (1,1<<16):
            with self.assertRaisesRegex(ValueError,'surface reference'):
                decode_surface(fixture(identifier))
        data=fixture()
        struct.pack_into('<H',data,56+84*2+0x6c4+4*16+6,1)
        with self.assertRaisesRegex(ValueError,'descriptor polygon'):
            decode_surface(data)
