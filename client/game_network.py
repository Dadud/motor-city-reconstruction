"""Recovered game-network task envelope for lobby follow-up work.

The dispatcher at 0x454d50 reads a uint32 task kind and forwards arguments
starting at byte offset 12. This module validates those envelopes only; it
does not open sockets or join races.
"""
import struct
from dataclasses import dataclass

from client.lobby_channels import (
    GAME_NETWORK_TASK_CHANNEL_ADD,
    GAME_NETWORK_TASK_GAME_START,
    GAME_NETWORK_TASK_MINI_ROOM_LIST,
    GAME_NETWORK_TASK_SERVER_CONNECT,
    KNOWN_GAME_NETWORK_TASKS,
    normalize_task_result,
)

_HEADER = struct.Struct('<I')
_ARGUMENT_OFFSET = 12


@dataclass(frozen=True)
class GameNetworkTask:
    kind: int
    argument: bytes

    @classmethod
    def decode(cls, payload: bytes):
        if len(payload) < _ARGUMENT_OFFSET:
            raise ValueError('game-network task payload is truncated')
        kind = _HEADER.unpack_from(payload)[0]
        if kind not in KNOWN_GAME_NETWORK_TASKS:
            raise ValueError('unknown game network task kind')
        return cls(kind, payload[_ARGUMENT_OFFSET:])

    def encode(self) -> bytes:
        if self.kind not in KNOWN_GAME_NETWORK_TASKS:
            raise ValueError('unknown game network task kind')
        if not isinstance(self.argument, bytes):
            raise ValueError('task argument must be bytes')
        return _HEADER.pack(self.kind) + bytes(_ARGUMENT_OFFSET - 4) + self.argument

    def normalized_result(self, native_result: int) -> int:
        return normalize_task_result(self.kind, native_result)


def race_entry_task_kinds():
    """Task kinds observed on the path toward rooms and game start."""
    return (
        GAME_NETWORK_TASK_SERVER_CONNECT,
        GAME_NETWORK_TASK_GAME_START,
        GAME_NETWORK_TASK_CHANNEL_ADD,
        GAME_NETWORK_TASK_MINI_ROOM_LIST,
    )
