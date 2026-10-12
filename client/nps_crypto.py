"""Recovered SHA-1 mask expansion from the legacy login session path.

0x7c7cb0 hashes seed plus a big-endian uint32 counter starting at zero.
0x7b69b0 selects big-endian counter bytes; 0x7d22a0/0x7d22e0 identify SHA-1.
Padding at 0x7c7a80 uses an empty-label hash, a 20-byte seed and two masks.
Full login/session behavior remains unverified.
"""
import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path


def mask_sha1(seed, length):
    """MGF1-style mask bytes; caller combines them with its destination.

    Bound to the recovered login string capacity, not a general crypto API.
    """
    if not isinstance(seed, bytes):
        raise TypeError('mask seed must be bytes')
    if len(seed) > 512:
        raise ValueError('mask seed exceeds supported login size')
    if type(length) is not int or not 0 <= length <= 512:
        raise ValueError('mask length must be within [0, 512]')
    return b''.join(hashlib.sha1(seed + struct.pack('>I', counter)).digest()
                    for counter in range((length + 19)//20))[:length]


def encode_oaep_sha1(message, size, seed):
    """Recovered empty-label OAEP layout, with an explicit replayable seed.

    The caller must provide a fresh unpredictable 20-byte seed for live use.
    No native time-seeded random-pool behavior is reproduced here.
    """
    if not isinstance(message, bytes) or not isinstance(seed, bytes):
        raise TypeError('message and seed must be bytes')
    if type(size) is not int or not 42 <= size <= 256:
        raise ValueError('RSA block size must be within [42, 256]')
    if len(seed) != 20 or len(message) > size - 42:
        raise ValueError('wrong seed size or message too long for OAEP block')
    data = (hashlib.sha1(b'').digest() + b'\0'*(size-len(message)-42)
            + b'\x01' + message)
    masked_data = bytes(a ^ b for a, b in zip(data, mask_sha1(seed, len(data))))
    masked_seed = bytes(a ^ b for a, b in zip(seed, mask_sha1(masked_data, 20)))
    return b'\0' + masked_seed + masked_data


class _DER:
    def __init__(self, data):
        self.data, self.cursor = data, 0

    def read(self, tag):
        if self.cursor + 2 > len(self.data) or self.data[self.cursor] != tag:
            raise ValueError('unexpected or truncated DER field')
        self.cursor += 1
        length = self.data[self.cursor]
        self.cursor += 1
        if length & 128:
            count = length & 127
            if not 1 <= count <= 2 or self.cursor + count > len(self.data):
                raise ValueError('invalid DER length')
            encoded = self.data[self.cursor:self.cursor+count]
            self.cursor += count
            length = int.from_bytes(encoded, 'big')
            if encoded[0] == 0 or length < 128:
                raise ValueError('noncanonical DER length')
        if self.cursor + length > len(self.data):
            raise ValueError('truncated DER content')
        result = self.data[self.cursor:self.cursor+length]
        self.cursor += length
        return result

    def finish(self):
        if self.cursor != len(self.data):
            raise ValueError('unexpected trailing DER content')


def _positive_integer(reader):
    data = reader.read(2)
    if not data or data[0] & 128 or (len(data) > 1 and data[0] == 0 and data[1] < 128):
        raise ValueError('RSA integer must be positive and canonically encoded')
    return int.from_bytes(data, 'big')


@dataclass(frozen=True)
class PublicKey:
    modulus: int
    exponent: int

    @property
    def size(self):
        return (self.modulus.bit_length() + 7)//8

    @classmethod
    def from_hex_spki(cls, data):
        """Parse the observed hexadecimal RSA SubjectPublicKeyInfo file format."""
        if not isinstance(data, bytes) or len(data) > 2048:
            raise ValueError('public key must be bounded hexadecimal bytes')
        try:
            text = data.decode('ascii')
            if any(c not in '0123456789abcdefABCDEF \r\n\t' for c in text):
                raise ValueError('invalid public-key hexadecimal')
            raw = bytes.fromhex(text)
        except (UnicodeError, ValueError) as error:
            raise ValueError('invalid public-key hexadecimal') from error
        top = _DER(raw)
        spki = _DER(top.read(0x30))
        top.finish()
        algorithm = _DER(spki.read(0x30))
        if algorithm.read(6) != bytes.fromhex('2a864886f70d010101'):
            raise ValueError('public key algorithm must be RSA')
        if algorithm.read(5) != b'':
            raise ValueError('invalid RSA algorithm parameters')
        algorithm.finish()
        bits = spki.read(3)
        spki.finish()
        if not bits or bits[0] != 0:
            raise ValueError('RSA bit string must have zero unused bits')
        bit_reader = _DER(bits[1:])
        rsa = _DER(bit_reader.read(0x30))
        bit_reader.finish()
        modulus, exponent = _positive_integer(rsa), _positive_integer(rsa)
        rsa.finish()
        if not 512 <= modulus.bit_length() <= 2048 or modulus % 2 != 1:
            raise ValueError('unsupported RSA modulus')
        if not 3 <= exponent <= 0xffffffff or exponent % 2 != 1 or exponent >= modulus:
            raise ValueError('invalid RSA exponent')
        return cls(modulus, exponent)

    def encrypt_hex(self, message, seed):
        """RSA public operation on recovered padding, formatted as uppercase hex."""
        block = encode_oaep_sha1(message, self.size, seed)
        value = int.from_bytes(block, 'big')
        if value >= self.modulus:
            raise ValueError('padded message exceeds public modulus')
        encrypted = pow(value, self.exponent, self.modulus).to_bytes(self.size, 'big')
        return encrypted.hex().upper().encode('ascii')


def installed_public_key(root):
    path = Path(root)/'pub.key'
    if path.stat().st_size > 2048:
        raise ValueError('public key exceeds supported size')
    return PublicKey.from_hex_spki(path.read_bytes())
