import struct
import unittest

from client.world_body_initialization import initialize_world_body


class WorldBodyInitializationTests(unittest.TestCase):
    @staticmethod
    def record(*, optional_transform=False, mass=12.0, material=0):
        image = bytearray(0x4F8)
        descriptor = 0x418
        struct.pack_into('<4f', image, descriptor, 1.0, 2.0, 3.0, mass)
        struct.pack_into('<9f', image, descriptor + 0x14,
                         1., 0., 0., 0., 1., 0., 0., 0., 1.)
        struct.pack_into('<3f', image, descriptor + 0x38, 1.0, 2.0, 3.0)
        struct.pack_into('<I', image, descriptor + 0x44, 0x12345678)
        struct.pack_into('<HH', image, descriptor + 0x48, 0, material)
        struct.pack_into('<I', image, descriptor + 0x50, 0xAABBCCDD)
        struct.pack_into('<9I', image, descriptor + 0x54, *range(9))
        struct.pack_into('<f', image, descriptor + 0x78, 0.5)
        struct.pack_into('<I', image, descriptor + 0x7C,
                         int(optional_transform))
        struct.pack_into('<f', image, descriptor + 0x80, 0.5)
        struct.pack_into('<f', image, descriptor + 0x84, 1.5)
        image[descriptor + 0x88:descriptor + 0x88 + 11] = b'GARBAGECAN\0'
        return image

    def test_normalizes_descriptor_constructs_body_and_calls_native_boundaries(self):
        image = self.record(mass=12.0)
        calls = []

        def query(owner, descriptor, query_record):
            calls.append(('query', len(descriptor), struct.unpack_from('<ii', query_record)))
            query_record[8:12] = b'WXYZ'
            return query_record

        def contact(owner, query_id, descriptor, argument):
            calls.append(('contact', query_id, len(descriptor), argument))
            struct.pack_into('<3f', owner, 8, 90., 91., 92.)

        result = initialize_world_body(
            image, collision_classes={'GARBAGECAN': 0x77},
            query_surface=query, setup_contact=contact,
            geometry_dispatch=lambda *_args: None, half_turn_matrix=None)
        self.assertIs(result, image)
        self.assertEqual(calls, [('query', 0xE0, (0x12345678, 0x02468ACF)),
                                 ('contact', 0x12345678, 0xE0, 0x18)])
        self.assertEqual(struct.unpack_from('<I', image, 0x4C4)[0], 0x77)
        self.assertEqual(struct.unpack_from('<9I', image, 0x4C8), tuple(range(9)))
        self.assertEqual(struct.unpack_from('<I', image, 0x4C0)[0], 0xAABBCCDD)
        self.assertEqual(struct.unpack_from('<3f', image, 8), (1., 2., 3.))
        self.assertEqual(struct.unpack_from('<f', image, 0x424)[0], 25.)
        self.assertEqual(struct.unpack_from('<f', image, 0x428)[0], 0.)
        self.assertEqual(struct.unpack_from('<3f', image, 0xCC), (1., 2., 3.))
        self.assertEqual(image[4], 0)
        self.assertEqual(image[6], 0)
        self.assertEqual(image[0x378:0x37C], b'WXYZ')
        self.assertEqual(struct.unpack_from('<f', image, 0x68)[0], 1.)
        self.assertAlmostEqual(struct.unpack_from('<f', image, 0x60)[0], 1.)
        self.assertAlmostEqual(struct.unpack_from('<f', image, 0x308)[0], 0.155)

    def test_fallback_class_uses_decoded_material_enum(self):
        for code, expected in ((0, 0x11), (1, 0x0F), (2, 0x14),
                               (3, 0x13), (4, 0x0F), (5, 0x12),
                               (6, 0x10), (7, 0x11)):
            image = self.record(material=code)
            image[0x4A0:0x4F8] = bytes(0x58)
            initialize_world_body(
                image, collision_classes={},
                query_surface=lambda _owner, _descriptor, query: query,
                setup_contact=lambda *_args: None,
                geometry_dispatch=lambda *_args: None, half_turn_matrix=None)
            self.assertEqual(struct.unpack_from('<I', image, 0x4C4)[0], expected)

    def test_optional_descriptor_transform_requires_and_uses_child_matrix(self):
        image = self.record(optional_transform=True)
        angles = []
        initialize_world_body(
            image, collision_classes={},
            query_surface=lambda _owner, _descriptor, query: query,
            setup_contact=lambda *_args: None,
            geometry_dispatch=lambda *_args: None,
            half_turn_matrix=lambda angle: angles.append(angle) or
            (1., 0., 0., 0., 1., 0., 0., 0., 1.))
        self.assertEqual(angles, [0.5])

    def test_unwritten_query_stack_tail_is_preserved_as_supplied(self):
        image = self.record()
        initial = bytearray((index * 29 + 7) & 0xFF for index in range(0x44))
        observed = []
        initialize_world_body(
            image, collision_classes={},
            query_surface=lambda _owner, _descriptor, query: observed.append(bytes(query)) or query,
            setup_contact=lambda *_args: None,
            geometry_dispatch=lambda *_args: None,
            initial_query_image=initial)
        self.assertEqual(observed[0][:8], struct.pack('<II', 0x12345678, 0x02468ACF))
        self.assertEqual(observed[0][8:], initial[8:])
        self.assertEqual(image[0x378:0x3B4], initial[8:0x44])


if __name__ == '__main__':
    unittest.main()
