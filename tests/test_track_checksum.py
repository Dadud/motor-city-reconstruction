import unittest
import zlib

from client.track_checksum import track_checksum


class TrackChecksumTests(unittest.TestCase):
    def test_raw_crc_accumulator_has_no_final_xor(self):
        for data in (b'', b'a', b'123456789', bytes(range(256)),
                     bytes(range(256)) * 257):
            with self.subTest(length=len(data)):
                self.assertEqual(track_checksum(data), zlib.crc32(data) ^ 0xffffffff)
        self.assertEqual(track_checksum(b''), 0xffffffff)
        self.assertEqual(track_checksum(b'123456789'), 0x340bc6d9)

    def test_accepts_mutable_and_view_inputs(self):
        data = b'motor city online'
        self.assertEqual(track_checksum(bytearray(data)), track_checksum(data))
        self.assertEqual(track_checksum(memoryview(data)), track_checksum(data))

    def test_rejects_non_bytes_input(self):
        with self.assertRaises(TypeError):
            track_checksum('track')


if __name__ == '__main__':
    unittest.main()
