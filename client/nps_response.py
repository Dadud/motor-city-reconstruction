"""Recovered 0x601 success payload (0x72bf90) and nested record readers.

Names describe observed placement/use; unknown values remain uninterpreted.
No network authentication or session cipher is established by decoding alone.
"""
from dataclasses import dataclass, field
import struct


class _Reader:
    def __init__(self, data):
        if not isinstance(data, bytes):
            raise TypeError('response payload must be bytes')
        if len(data) > 65523:
            raise ValueError('response exceeds framed payload capacity')
        self.data, self.cursor = data, 0

    def take(self, size):
        if self.cursor + size > len(self.data):
            raise ValueError('truncated login success payload')
        value = self.data[self.cursor:self.cursor+size]
        self.cursor += size
        return value

    def u32(self):
        return struct.unpack('>I', self.take(4))[0]

    def counted(self, capacity):
        size = struct.unpack('>H', self.take(2))[0]
        if size > capacity:
            raise ValueError('response field exceeds native capacity')
        return self.take(size)

    def nested(self):
        size = struct.unpack('>H', self.take(2))[0]
        return _Reader(self.take(size))

    def finish(self):
        if self.cursor != len(self.data):
            raise ValueError('unexpected trailing response data')


@dataclass(frozen=True)
class AuthorizationRecord:
    value: int
    enabled: int
    expires_at: int
    name: bytes = field(repr=False)
    text_1: bytes = field(repr=False)
    text_2: bytes = field(repr=False)

    def active_at(self, unix_seconds):
        """Native 0x72bd80: nonzero enabled and no expiry or now before expiry."""
        if type(unix_seconds) is not int or not 0 <= unix_seconds <= 0x7fffffff:
            raise ValueError('time must fit original nonnegative signed time_t')
        # Native comparison reads the expiry field as signed 32-bit.
        expiry = self.expires_at if self.expires_at < 0x80000000 else self.expires_at - 2**32
        return bool(self.enabled) and (expiry == 0 or unix_seconds < expiry)

    @classmethod
    def _read(cls, reader):
        value = cls(reader.u32(), reader.u32(), reader.u32(),
                    reader.counted(64), reader.counted(256), reader.counted(256))
        reader.finish()
        return value


@dataclass(frozen=True)
class SessionKeyRecord:
    material: bytes = field(repr=False)
    value: int

    def encode(self):
        """Header-free key record used as the login RSA plaintext (0x71d6d0)."""
        if not isinstance(self.material, bytes) or len(self.material) > 32:
            raise ValueError('session material must contain at most 32 bytes')
        if type(self.value) is not int or not 0 <= self.value <= 0xffffffff:
            raise ValueError('session record value must fit uint32')
        return struct.pack('>H', len(self.material)) + self.material + struct.pack('>I', self.value)

    @classmethod
    def _read(cls, reader):
        value = cls(reader.counted(32), reader.u32())
        reader.finish()
        return value


@dataclass(frozen=True)
class LoginSuccess:
    user_id: int
    value_2: int
    flag: bool
    authorization_1: AuthorizationRecord
    authorization_2: AuthorizationRecord
    session: SessionKeyRecord
    value_3: int
    text: bytes = field(repr=False)

    @classmethod
    def decode(cls, payload):
        reader = _Reader(payload)
        user_id, value_2 = reader.u32(), reader.u32()
        flag = reader.take(1)[0] != 0
        first = AuthorizationRecord._read(reader.nested())
        second = AuthorizationRecord._read(reader.nested())
        session = SessionKeyRecord._read(reader.nested())
        value = cls(user_id, value_2, flag, first, second, session,
                    reader.u32(), reader.counted(64))
        reader.finish()
        return value
