"""Recovered game-network task envelope for lobby follow-up work.

The dispatcher at 0x454d50 reads a uint32 task kind and forwards arguments
starting at byte offset 12. This module validates those envelopes only; it
does not open sockets or join races.
"""
import struct
from dataclasses import dataclass

from client.lobby_channels import KNOWN_GAME_NETWORK_TASKS, normalize_task_result

_HEADER = struct.Struct('<I')
_ARGUMENT_OFFSET = 12


@dataclass(frozen=True)
class GameNetworkTask:
    kind: int
    argument: bytes
    opaque_header: bytes = bytes(8)

    @property
    def operation_id(self):
        """Local worker correlation ID, not a network transaction ID."""
        return struct.unpack('<II', self.opaque_header)[0]

    @property
    def worker_result_bits(self):
        """Local result bits; valid only after observed worker completion."""
        return struct.unpack('<II', self.opaque_header)[1]

    @classmethod
    def decode(cls, payload: bytes):
        if len(payload) < _ARGUMENT_OFFSET:
            raise ValueError('game-network task payload is truncated')
        kind = _HEADER.unpack_from(payload)[0]
        if kind not in KNOWN_GAME_NETWORK_TASKS:
            raise ValueError('unknown game network task kind')
        return cls(kind, payload[_ARGUMENT_OFFSET:], payload[4:_ARGUMENT_OFFSET])

    def encode(self) -> bytes:
        if self.kind not in KNOWN_GAME_NETWORK_TASKS:
            raise ValueError('unknown game network task kind')
        if not isinstance(self.argument, bytes):
            raise ValueError('task argument must be bytes')
        if not isinstance(self.opaque_header, bytes) or len(self.opaque_header) != 8:
            raise ValueError('opaque task header must be eight bytes')
        return _HEADER.pack(self.kind) + self.opaque_header + self.argument

    def normalized_result(self, native_result: int) -> int:
        return normalize_task_result(self.kind, native_result)


def dispatched_task_kinds() -> frozenset[int]:
    """Independent cases of 0x454d50; this set specifies no execution order."""
    return KNOWN_GAME_NETWORK_TASKS
