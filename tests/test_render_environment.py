import unittest
import struct

from client.render_environment import (release_environment_objects,
                                       build_environment_mesh_no_projection,
                                       set_environment_activity)


class RenderEnvironmentTests(unittest.TestCase):
    def test_optional_objects_get_ordered_activity_writes(self):
        self.assertEqual(set_environment_activity(0x1000,0x2000),
                         ((0x1000,1),(0x2000,0)))

    def test_null_objects_are_not_written(self):
        self.assertEqual(set_environment_activity(0,0x2000),
                         (None,(0x2000,0)))
        self.assertEqual(set_environment_activity(0,0),(None,None))

    def test_addresses_must_be_nonnegative_integers(self):
        for value in (-1,1.0,True):
            with self.assertRaises(ValueError):
                set_environment_activity(value,0)

    def test_cleanup_preserves_free_order_and_clears_all_globals(self):
        self.assertEqual(release_environment_objects(
            (0x1000,0,0x3000,0x4000)),
            ((0x1000,0x3000,0x4000),(0,0,0,0)))

    def test_cleanup_rejects_wrong_shape_or_non_word_pointers(self):
        for objects in ((0,0,0), (0,0,0,1<<32), (0,0,0,True)):
            with self.assertRaises(ValueError):
                release_environment_objects(objects)

    def test_mesh_builder_fills_rows_and_preserves_unwritten_allocation_bytes(self):
        row=bytearray(0x54)
        for offset,value in ((0,1.),(4,2.),(8,3.),(0x18,.5),(0x1c,.25),
                             (0x20,.75),(0x24,1.),(0x28,2.),(0x2c,3.),
                             (0x38,.5),(0x3c,2.)):
            struct.pack_into('<f',row,offset,value)
        struct.pack_into('<ii',row,0x44,2,1)
        initial=bytes([0xa5])*0x3d0
        result=build_environment_mesh_no_projection(
            row,3,17,False,initial,vertical_step=.25,
            segment_step=.1,span_scale=.5)
        self.assertEqual(struct.unpack_from('<ii',result),(3,17))
        self.assertEqual(struct.unpack_from('<6f',result,8),
                         (4.5,7.,11.25,1.5,5.5,6.75))
        self.assertEqual(result[0x114:0x120],initial[0x114:0x120])
        self.assertEqual(struct.unpack_from('<I',result,0x120)[0],0xffffffff)


if __name__=='__main__':
    unittest.main()
