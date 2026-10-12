import struct
import unittest
from client.track import decode_track


def fixture():
    data=bytearray(56+84*2)
    struct.pack_into('<I',data,0,0xfeeeeb19)
    struct.pack_into('<II',data,44,0,2)
    for i in range(2):
        struct.pack_into('<14f',data,56+i*84,0,0,i*5,0,1,0,0,0,1,1,0,0,3,4)
    return data


class TrackTests(unittest.TestCase):
    def test_vectors_and_corridor_topology(self):
        track=decode_track(fixture())
        self.assertEqual(track.slices[1].position,(0,0,5))
        part=track.corridor().parts[0]
        self.assertEqual(part.vertices,((-3,0,0),(4,0,0),(-3,0,5),(4,0,5)))
        self.assertEqual(len(part.triangles),2)
        self.assertEqual(track.remaining_bytes,0)

    def test_bad_magic_truncated_and_budget(self):
        for data in (fixture()[:55],fixture()[:-1],bytes(len(fixture()))):
            with self.assertRaises(ValueError):decode_track(data)
        data=fixture();struct.pack_into('<I',data,48,100001)
        with self.assertRaisesRegex(ValueError,'budget'):decode_track(data)

    def test_nonfinite_and_degenerate_basis(self):
        data=fixture();struct.pack_into('<f',data,56,float('nan'))
        with self.assertRaisesRegex(ValueError,'non-finite'):decode_track(data)
        data=fixture();struct.pack_into('<3f',data,56+12,0,0,0)
        with self.assertRaisesRegex(ValueError,'basis'):decode_track(data)
