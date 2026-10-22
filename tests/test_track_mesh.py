import struct
import unittest
from client.track_object_bounds import build_track_object_bounds
from client.track_object_mesh import decode_track_object_group
from client.track_mesh import (TrackObject, TrackObjectGroup, decode_mesh)
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

    def test_attached_object_payload_is_retained(self):
        source=fixture()
        vertex_start = 56 + 84 * 2 + 0x6c4 + 4 * 16 + 32 + 56 + 3
        source[vertex_start:vertex_start + 16] = bytes(range(16))
        groups=[]
        decode_mesh(source,object_records=groups)
        self.assertEqual(len(groups),1)
        group=groups[0]
        self.assertEqual((group.block_index,group.section_offset),(0,0x640))
        self.assertEqual(len(group.objects),1)
        obj=group.objects[0]
        self.assertEqual(obj.animation,b'abc')
        self.assertEqual(obj.vertex_records,(bytes(range(12)),))
        self.assertEqual(obj.vertex_attributes,(bytes(range(12,16)),))
        self.assertEqual(obj.faces,())
        self.assertEqual(len(obj.descriptor),56)

    def test_decoded_track_objects_feed_runtime_bounds_producer(self):
        source = fixture()
        descriptor = 56 + 84 * 2 + 0x6c4 + 4 * 16 + 32
        struct.pack_into('<H', source, descriptor + 2, 3)
        groups = []
        decode_mesh(source, object_records=groups)
        result = build_track_object_bounds(
            groups[0], source_address=0x71001000,
            table_address=0x71004000, payload_address=0x71001038)
        candidates = result.candidates
        row = candidates.records[:0x78]
        self.assertEqual(struct.unpack_from('<I', row, 0x30)[0], 0)
        self.assertEqual(struct.unpack_from('<3f', row, 0x4c),
                         (0.0, 0.0, 0.0))
        self.assertEqual(struct.unpack_from('<3f', row, 0x3c),
                         (0.0, 0.0, 0.0))
        self.assertEqual(struct.unpack_from('<H', candidates.sources, 2)[0], 5)
        self.assertEqual(struct.unpack_from('<I', candidates.sources, 0x28)[0],
                         0x7100103b)
        self.assertEqual(struct.unpack_from('<H', result.source_rows, 2)[0], 3)
        self.assertEqual(result.vertex_arrays,
                         ((0x7100103b, struct.pack('<3f', 0.0, 0.0, 0.0)),))

    def test_object_quad_becomes_two_local_triangles_with_native_uv_order(self):
        descriptor = bytearray(56)
        struct.pack_into('<I', descriptor, 36, 4)
        struct.pack_into('<I', descriptor, 48, 1)
        face = (3, 2, 1, 0, 0, 1, 2, 3, 0, 1, 2, 3, 0, 7, 0x8000)
        obj = TrackObject(
            bytes(descriptor), b'',
            (struct.pack('<3f', 0, 0, 0), struct.pack('<3f', 1, 0, 0),
             struct.pack('<3f', 1, 1, 0), struct.pack('<3f', 0, 1, 0)),
            (bytes(4),) * 4, (face,))
        group = TrackObjectGroup(2, 0x640, (obj,))
        model = decode_track_object_group(group, (0.0, 0.25, 0.5, 0.75))
        self.assertEqual(model.triangle_count, 2)
        first, second = model.parts[0].triangles
        self.assertEqual(first.indices, (3, 2, 1))
        self.assertEqual(first.uv, (0.5, 0.0, 0.5, 0.75, 0.25, 0.75))
        self.assertEqual((first.texture_page, first.flags), (7, 0x8000))
        self.assertEqual(second.indices, (3, 1, 0))
        self.assertEqual(model.parts[0].normals[0][2], -1.0)

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
