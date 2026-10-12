import struct
import unittest
from client.track_mesh import decode_mesh
from test_track import fixture as road_fixture


def fixture():
    road=road_fixture()
    header=bytearray(0x6c4)
    struct.pack_into('<I',header,4*4,1)
    struct.pack_into('<I',header,0x134,4)
    struct.pack_into('<I',header,0x640,1)
    vertices=struct.pack('<12f',0,0,0,1,0,0,1,0,1,0,0,1)
    face=struct.pack('<4H',0,1,2,3)+bytes(22)+bytes(2)
    obj=bytearray(56)
    struct.pack_into('<I',obj,28,3)
    struct.pack_into('<I',obj,36,1)
    return road+header+vertices+bytes(16)+face+obj+b'abc'+bytes(16)


class TrackMeshTests(unittest.TestCase):
    def test_native_uv_table_corner_order_and_texture_index(self):
        source=fixture()
        struct.pack_into('<I',source,52,4)
        face=56+84*2+0x6c4+4*16
        struct.pack_into('<8H',source,face+8,0,1,1,0,2,3,3,2)
        struct.pack_into('<HH',source,face+26,9,0x8000)
        source+=bytes(8)+struct.pack('<4f',0,0.5,1,2)
        model,end=decode_mesh(source,materials=True)
        triangle=model.parts[0].triangles[0]
        self.assertEqual(triangle.uv,(0.5,0,2,0,0.5,1))
        self.assertEqual((triangle.texture_page,triangle.flags),(9,0x8000))
        self.assertEqual(end,len(source))
        struct.pack_into('<H',source,face+8,4)
        with self.assertRaisesRegex(ValueError,'UV index'):decode_mesh(source,materials=True)

    def test_quad_split_object_byte_length_and_alignment(self):
        source=fixture()
        model,end=decode_mesh(source)
        self.assertEqual(end,len(source))
        self.assertEqual(model.triangle_count,2)
        self.assertEqual(model.parts[0].triangles[1].indices,(0,2,3))
        self.assertEqual(model.parts[0].vertices[2],(1,0,1))

    def test_invalid_indices_and_truncated_object_are_rejected(self):
        source=fixture()
        with self.assertRaisesRegex(ValueError,'EOF'):decode_mesh(source[:-1])
        source=fixture()
        face_start=56+84*2+0x6c4+4*16
        struct.pack_into('<H',source,face_start,4)
        with self.assertRaisesRegex(ValueError,'index outside'):decode_mesh(source)

    def test_nonfinite_vertex_and_excessive_geometry(self):
        source=fixture();start=56+84*2+0x6c4
        struct.pack_into('<f',source,start,float('inf'))
        with self.assertRaisesRegex(ValueError,'non-finite'):decode_mesh(source)
        source=fixture();struct.pack_into('<I',source,56+84*2+0x134,2_000_001)
        with self.assertRaisesRegex(ValueError,'budget'):decode_mesh(source)
