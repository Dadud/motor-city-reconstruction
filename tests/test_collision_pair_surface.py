import struct
import unittest

from client.body_constructor import construct_body
from client.collision_pair_surface import resolve_pair_surface


class CollisionPairSurfaceTests(unittest.TestCase):
    def body(self, position=(0., -.2, 0.), velocity=(0., -1., 0.)):
        image = bytearray(construct_body(bytes(0x2000), 0x71008000,
                                         800., (1., 1., 1.), 0, 2))
        struct.pack_into('<3f', image, 8, *position)
        struct.pack_into('<3f', image, 0x14, *velocity)
        # Keep the original full 22-point body geometry branch.
        struct.pack_into('<h', image, 0x3bc, 1)
        return bytes(image)

    def test_rejects_when_no_vertex_is_below_the_height_limit(self):
        body = self.body()
        result = resolve_pair_surface(body, 0x71008000, (0., 1., 0.),
                                      (0., 0., 0.), 1., .45, .2, -5.)
        self.assertFalse(result.collided)
        self.assertIsNone(result.selected_vertex)
        self.assertEqual(result.body_image, body)

    def test_selects_inward_vertex_and_corrects_cached_world_points(self):
        body = self.body()
        result = resolve_pair_surface(body, 0x71008000, (0., 1., 0.),
                                      (0., 0., 0.), 1., .45, .2, 1.)
        self.assertIsNotNone(result.selected_vertex)
        self.assertGreater(result.penetration, 0.)
        position = struct.unpack_from('<3f', result.body_image, 8)
        self.assertGreater(position[1], -.2)
        self.assertEqual(result.collided, result.impulse_samples > 0)


if __name__ == '__main__':
    unittest.main()
