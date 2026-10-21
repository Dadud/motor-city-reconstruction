import struct
import unittest

from client.owner_startup import initialize_owner_startup
from client.fce import Model, Part, Triangle
from client.raster_scene import RasterSceneNode
from tools.startup_record_oracle import configuration, model_image, owner_image


class OwnerStartupTests(unittest.TestCase):
    def scene(self):
        model = Model((Part('body', (0., 0., 0.),
            ((-2., -1., 0.), (2., -1., 0.), (0., 3., 0.)),
            ((0., 0., 1.),) * 3,
            (Triangle((0, 1, 2), (0., 0., 1., 0., .5, 1.), 0, 0),)),),
            0x101014)
        return model, (RasterSceneNode(model, 0, 0),)

    def inputs(self):
        owner = owner_image(0, 0.)
        config = bytearray(configuration(0, 4))
        struct.pack_into('<i', config, 0x48, 2)
        # The body phase reads observed pre-existing markers/levers in this order.
        struct.pack_into('<f', owner, 0x18c4, 1.4)
        struct.pack_into('<f', owner, 0x18c8, -1.3)
        struct.pack_into('<f', owner, 0x18b8, .2)
        return bytes(owner), bytes(config)

    def test_connected_phases_publish_record_and_preserve_owner_size(self):
        _, nodes = self.scene()
        model = model_image(False)
        owner, config = self.inputs()
        result = initialize_owner_startup(owner, config, model, (.7, .6, 1.8),
                                          nodes, 0, assembly_finalized=True)
        self.assertEqual(len(result.owner), 0x2000)
        self.assertEqual(len(result.startup_record), 0x4a8)
        self.assertGreater(result.scene_area, 0.)
        self.assertEqual(result.owner[0x17ec:0x1c94], result.startup_record)
        self.assertEqual(struct.unpack_from('<f', result.startup_record, 0xd4)[0],
                         result.scene_area)
        self.assertGreater(struct.unpack_from('<f', result.owner, 0x6b8)[0], 0.)

    def test_requires_authentic_upstream_observations(self):
        _, nodes = self.scene()
        model = model_image(False)
        owner, config = self.inputs()
        with self.assertRaisesRegex(ValueError, 'assembly'):
            initialize_owner_startup(owner, config, model, (.7, .6, 1.8),
                                     nodes, 0, assembly_finalized=False)
        with self.assertRaisesRegex(ValueError, 'scene nodes'):
            initialize_owner_startup(owner, config, model, (.7, .6, 1.8),
                                     (), 0, assembly_finalized=True)


if __name__ == '__main__':
    unittest.main()
