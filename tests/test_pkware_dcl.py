import struct
import unittest
from client.pkware_dcl import explode, decompress_mcots_payload


class PKWareDCLTests(unittest.TestCase):
    # Published blast 1.3 example, exercising overlapping length/distance copy.
    VECTOR = bytes.fromhex('00048224258f807f')
    OUTPUT = b'AIAIAIAIAIAIA'

    def test_upstream_overlap_vector_and_mcots_length(self):
        self.assertEqual(explode(self.VECTOR), self.OUTPUT)
        payload = struct.pack('<H', len(self.OUTPUT))+self.VECTOR
        self.assertEqual(decompress_mcots_payload(payload), self.OUTPUT)
        self.assertEqual(explode(self.VECTOR+b'ignored'), self.OUTPUT)

    def test_all_truncations_rejected(self):
        for size in range(len(self.VECTOR)):
            with self.assertRaises(ValueError):
                explode(self.VECTOR[:size])

    def test_bad_headers_and_output_bounds(self):
        for stream in (b'\x02\x04'+self.VECTOR[2:], b'\0\x03'+self.VECTOR[2:], b'\0\x07'+self.VECTOR[2:]):
            with self.assertRaises(ValueError):
                explode(stream)
        with self.assertRaises(ValueError):
            explode(self.VECTOR, max_output=12)
        for length in (0, 12, 14, 65535):
            with self.assertRaises(ValueError):
                decompress_mcots_payload(struct.pack('<H', length)+self.VECTOR)
        for size in (-1, True, 65527):
            with self.assertRaises(ValueError):
                explode(self.VECTOR, max_output=size)
