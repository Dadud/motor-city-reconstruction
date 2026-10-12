import unittest
from client.fce import Part, Triangle, Model
from client.scene import place_part, texture_slots


class SceneTests(unittest.TestCase):
    def test_mount_origin_reflection_normals_and_texture_namespace(self):
        part = Part(':PHtire', (9, 9, 9), ((1, 2, 3),), ((1, 0, 0),),
                    (Triangle((0, 0, 0), (0,)*6, 1, 0),))
        placed = place_part(part, (4, 5, 6), mirror=True, page_offset=3)
        self.assertEqual(placed.origin, (4, 5, 6))
        self.assertEqual(placed.vertices, ((-1, 2, 3),))
        self.assertEqual(placed.normals, ((-1, 0, 0),))
        self.assertEqual(placed.triangles[0].texture_page, 4)
        self.assertEqual(part.vertices, ((1, 2, 3),))

    def test_missing_texture_pages_reserved_without_aliasing(self):
        part = Part('body', (0,)*3, (), (), (Triangle((0,)*3, (0,)*6, 2, 0),))
        source = Model((part,), 0x101015)
        self.assertEqual(texture_slots(source, ('image',)), ['image', None, None])
        self.assertEqual(texture_slots(source, ()), [None]*3)
        excessive = Model((Part('bad', (0,)*3, (), (),
                          (Triangle((0,)*3, (0,)*6, 256, 0),)),), 0x101015)
        with self.assertRaises(ValueError):
            texture_slots(excessive, ())
