import unittest

from client.nps_crypto import PublicKey, encode_oaep_sha1, mask_sha1


def der(tag, value):
    size = len(value)
    length = bytes([size]) if size < 128 else b'\x81' + bytes([size])
    return bytes([tag]) + length + value


def synthetic_spki():
    # A synthetic odd modulus tests parsing only, not a generated RSA key.
    integer = b'\x00\x80' + b'\x00'*126 + b'\x03'
    rsa = der(0x30, der(2, integer) + der(2, b'\x01\x00\x01'))
    algorithm = der(0x30, der(6, bytes.fromhex('2a864886f70d010101')) + der(5, b''))
    return der(0x30, algorithm + der(3, b'\x00' + rsa))


class PublicKeyTests(unittest.TestCase):
    def test_spki_structure_and_uppercase_ciphertext(self):
        key = PublicKey.from_hex_spki(synthetic_spki().hex().encode())
        self.assertEqual(key.size, 128)
        self.assertEqual(key.exponent, 65537)
        encrypted = key.encrypt_hex(b'x'*32, bytes(20))
        self.assertEqual(len(encrypted), 256)
        self.assertEqual(encrypted, encrypted.upper())

    def test_reject_bad_algorithm_lengths_and_trailing_bytes(self):
        raw = synthetic_spki()
        for data in (b'zz', raw[:-1].hex().encode(), (raw+b'x').hex().encode(),
                     raw.replace(bytes.fromhex('2a864886f70d010101'),
                                 bytes.fromhex('2a864886f70d010102')).hex().encode(),
                     b'0'*2049):
            with self.assertRaises(ValueError):
                PublicKey.from_hex_spki(data)

    def test_decode_padding_masks_and_separator(self):
        seed, message = bytes(range(20)), bytes(range(32))
        encoded = encode_oaep_sha1(message, 128, seed)
        self.assertEqual(len(encoded), 128)
        self.assertEqual(encoded[0], 0)
        recovered_seed = bytes(a ^ b for a, b in zip(encoded[1:21], mask_sha1(encoded[21:], 20)))
        self.assertEqual(recovered_seed, seed)
        data = bytes(a ^ b for a, b in zip(encoded[21:], mask_sha1(seed, 107)))
        self.assertEqual(data[:20].hex(), 'da39a3ee5e6b4b0d3255bfef95601890afd80709')
        self.assertEqual(data[20:], b'\0'*54 + b'\x01' + message)

    def test_padding_limits(self):
        for message, size, seed in ((b'x'*87, 128, bytes(20)),
                                     (b'', 41, bytes(20)),
                                     (b'', 257, bytes(20)),
                                     (b'', 128, bytes(19))):
            with self.assertRaises(ValueError):
                encode_oaep_sha1(message, size, seed)
