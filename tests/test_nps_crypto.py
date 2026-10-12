import unittest

from client.nps_crypto import mask_sha1


class MaskTests(unittest.TestCase):
    def test_first_counter_is_big_endian_zero(self):
        self.assertEqual(mask_sha1(b'', 20).hex(),
                         '9069ca78e7450a285173431b3e52c5c25299e473')

    def test_cross_digest_boundary_and_truncation(self):
        self.assertEqual(mask_sha1(b'', 21).hex(),
                         '9069ca78e7450a285173431b3e52c5c25299e47347')
        self.assertEqual(mask_sha1(b'seed', 0), b'')
        self.assertEqual(mask_sha1(b'seed', 19), mask_sha1(b'seed', 40)[:19])

    def test_bounds(self):
        for length in (-1, 513, True, 1.5):
            with self.assertRaises(ValueError):
                mask_sha1(b'', length)
        with self.assertRaises(ValueError):
            mask_sha1(b'x'*513, 1)
        with self.assertRaises(TypeError):
            mask_sha1('seed', 1)
