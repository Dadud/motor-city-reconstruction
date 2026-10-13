"""Connection login packing recovered from 0x7e47d0 and 0x7e5e60.

Field values whose game-level meaning remains unresolved are explicit inputs.
The connection login is sent directly before normal lobby encryption activates.
"""
from dataclasses import dataclass, field
import struct
import hashlib

from client.nps_framing import Frame


def session_key_digest(material):
    """Native connection login's 16-byte MD5 of retained session key bytes.

    This is the legacy wire digest, not a password hash or a new security design.
    """
    if not isinstance(material, bytes) or len(material) > 32:
        raise ValueError('session key must contain at most 32 bytes')
    return hashlib.md5(material, usedforsecurity=False).digest()


def _string(value, capacity):
    if not isinstance(value, bytes) or b'\0' in value or len(value) >= capacity:
        raise ValueError('login string must fit its native buffer without embedded NUL')
    terminated = value + b'\0'
    return struct.pack('>I', len(terminated)) + terminated


def _u32(value):
    if type(value) is not int or not 0 <= value <= 0xffffffff:
        raise ValueError('login integer must fit uint32')
    return struct.pack('>I', value)


@dataclass(frozen=True)
class LobbyLogin:
    user_id: int
    username: bytes = field(repr=False)
    key_blob: bytes = field(repr=False)
    value_100: int
    value_200: int
    version: bytes
    hostname: bytes = field(repr=False)
    ip_address: bytes = field(repr=False)
    opaque_16: bytes = field(repr=False)

    def payload(self):
        if not isinstance(self.key_blob, bytes) or len(self.key_blob) != 64:
            raise ValueError('login key blob must contain exactly 64 bytes')
        if not isinstance(self.opaque_16, bytes) or len(self.opaque_16) != 16:
            raise ValueError('login opaque field must contain exactly 16 bytes')
        body = (_u32(self.user_id) + _string(self.username, 32) + self.key_blob
                + _u32(self.value_100) + _u32(self.value_200)
                + _string(self.version, 32) + _string(self.hostname, 64)
                + _string(self.ip_address, 16) + self.opaque_16)
        # 0x7e4920 supplies 255 bytes of payload capacity to the native builder.
        if len(body) > 255:
            raise ValueError('connection login exceeds native payload capacity')
        return body

    def frame(self, *, message_id=0x100):
        if message_id not in (0x100, 0x301):
            raise ValueError('connection login ID must be 0x100 or 0x301')
        return Frame(message_id, self.payload())
