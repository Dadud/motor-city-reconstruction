import struct
import unittest

from client.render_projection import track_point_without_cached_geometry


class RenderProjectionTests(unittest.TestCase):
    def test_copies_xyz_from_selected_track_row(self):
        rows=[]
        for point in ((1.25,-2.5,3.75),(10.,20.,30.)):
            row=bytearray(0x54)
            struct.pack_into('<3f',row,0,*point)
            rows.append(bytes(row))
        self.assertEqual(track_point_without_cached_geometry(rows,1,0),
                         (10.,20.,30.))

    def test_rejects_cached_geometry_and_invalid_rows(self):
        row=bytes(0x54)
        with self.assertRaises(ValueError):
            track_point_without_cached_geometry((row,),0,1)
        with self.assertRaises(ValueError):
            track_point_without_cached_geometry((bytes(0x50),),0,0)


if __name__=='__main__':
    unittest.main()
