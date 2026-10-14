"""Bounded original local connection IDs and existing-connection identity lookup.

No sockets, authentication, allocation, registry ownership or locking occur here.
Caller-supplied entries must follow the original registry's traversal order.
"""
from dataclasses import dataclass
import struct


def _u32(value):
    if type(value) is not int or not 0 <= value <= 0xffffffff:
        raise ValueError('value must be a uint32')
    return value


def _signed(value):
    return value if value < 0x80000000 else value - 0x100000000


def allocate_connection_id(counter):
    """Constructor takes the old counter, then increments, including wrap to zero."""
    counter = _u32(counter)
    return counter, (counter + 1) & 0xffffffff


def _cstring(value):
    if not isinstance(value, bytes) or b'\0' not in value:
        raise ValueError('bounded input must contain a NUL terminator')
    return value.split(b'\0', 1)[0]


@dataclass(frozen=True)
class ConnectionRegistryEntry:
    connection_id: int
    username: bytes
    hostname: bytes
    port: int

    def __post_init__(self):
        _u32(self.connection_id)
        _u32(self.port)
        _cstring(self.username)
        _cstring(self.hostname)

    @classmethod
    def from_image(cls, image):
        if not isinstance(image, bytes) or len(image) < 0x178:
            raise ValueError('connection image must contain at least 0x178 bytes')
        return cls(struct.unpack_from('<I', image, 4)[0], image[0x10c:0x12c],
                   image[8:0x108], struct.unpack_from('<I', image, 0x174)[0])


def find_existing_connection(entries, username, hostname, port):
    """73df10: exact C-string identity and port; first match, otherwise -20."""
    username, hostname = _cstring(username), _cstring(hostname)
    port = _u32(port)
    for entry in entries:
        if not isinstance(entry, ConnectionRegistryEntry):
            raise ValueError('entries must be ConnectionRegistryEntry values')
        if (_cstring(entry.username) == username and
                _cstring(entry.hostname) == hostname and entry.port == port):
            return _signed(entry.connection_id)
    return -20
