import struct
import unittest
from client.textures import decode_fsh, unpack_qfs


def qfs(payload, size):
    return b'\x10\xfb' + size.to_bytes(3, 'big') + payload


def image(kind, width, height, pixels):
    entry = struct.pack('<IHH8x', kind, width, height) + pixels
    return b'SHPI' + struct.pack('<II4s4sI', 24+len(entry), 1, b'GIMX', b'test', 24) + entry


class TextureTests(unittest.TestCase):
    def test_qfs_literals_and_terminal(self):
        self.assertEqual(unpack_qfs(qfs(b'\xe0ABCD\xffXYZ', 7)), b'ABCDXYZ')

    def test_qfs_overlapping_backreferences_all_sizes(self):
        for command, count in ((b'\x00\x00', 3), (b'\x80\x00\x00', 4),
                               (b'\xc0\x00\x00\x00', 5)):
            with self.subTest(command=command):
                encoded = b'\xe0AAAA' + command + b'\xfc'
                self.assertEqual(unpack_qfs(qfs(encoded, 4+count)), b'A'*(4+count))

    def test_qfs_rejects_bad_distance_truncation_and_budget(self):
        for encoded in (qfs(b'\x00\x00\xfc', 3), qfs(b'\xe0ABC', 4),
                        qfs(b'\xfc', 1)):
            with self.assertRaises(ValueError):
                unpack_qfs(encoded)
        with self.assertRaisesRegex(ValueError, 'budget'):
            unpack_qfs(qfs(b'\xfc', 5), max_bytes=4)

    def test_bgra_and_argb1555_channels(self):
        self.assertEqual(decode_fsh(image(0x7d, 1, 1, bytes((3, 2, 1, 4))))[0].rgba,
                         bytes((1, 2, 3, 4)))
        self.assertEqual(decode_fsh(image(0x7e, 2, 1, struct.pack('<HH', 0xfc00, 0x001f)))[0].rgba,
                         bytes((255, 0, 0, 255, 0, 0, 255, 0)))

    def test_dxt1_transparent_selector_and_partial_block(self):
        pixels = struct.pack('<HHI', 0, 0xffff, 3)
        self.assertEqual(decode_fsh(image(0x60, 1, 1, pixels))[0].rgba, bytes(4))

    def test_dxt3_explicit_alpha(self):
        pixels = struct.pack('<QHHI', 8, 0xf800, 0, 0)
        self.assertEqual(decode_fsh(image(0x61, 1, 1, pixels))[0].rgba, bytes((255, 0, 0, 136)))

    def test_image_dimensions_truncation_and_budget(self):
        for encoded in (image(0x7d, 0, 1, b''), image(0x7d, 1, 1, b'abc')):
            with self.assertRaises(ValueError):
                decode_fsh(encoded)
        with self.assertRaisesRegex(ValueError, 'budget'):
            decode_fsh(image(0x7d, 2, 1, bytes(8)), max_pixels=1)


if __name__ == '__main__':
    unittest.main()
