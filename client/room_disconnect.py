"""Stable-state room disconnect preparation recovered from 0x44d750.

Local container resets, pending waits and actual scheduling are external. Only
the initialized task kind and eight argument bytes are exposed; the original
producer leaves the rest of its stack-local task record unspecified.
"""
from dataclasses import dataclass
import struct

ROOM_DISCONNECT_MIN_SIZE = 0x3ac


class PendingRoomOperation(ValueError):
    """Original connected path waits for a pending operation before preparing."""


@dataclass(frozen=True)
class RoomDisconnectPreparation:
    room_image: bytes
    argument: bytes | None
    tracked: bool
    immediate_return: int | None
    reset_owner_offsets: tuple[int, int] = (0x2e0, 0x1fc)

    @property
    def task_kind(self):
        return None if self.argument is None else 1


def prepare_room_disconnect(room_image: bytes, *, wait_for_completion: bool) -> RoomDisconnectPreparation:
    """Prepare from stable state, preserving selector, errors and unknown bytes.

    A connected pending operation needs the original wait/reevaluation first.
    Call again with the observed stable image; no busy loop is implemented here.
    Already disconnected rooms reset directly, even with a nonzero pending flag.
    """
    if not isinstance(room_image, bytes) or not ROOM_DISCONNECT_MIN_SIZE <= len(room_image) <= 65536:
        raise ValueError('expected bounded complete room image')
    if type(wait_for_completion) is not bool:
        raise ValueError('wait switch must be boolean')
    connected = struct.unpack_from('<H', room_image, 0xec)[0] != 0
    pending = struct.unpack_from('<I', room_image, 0x3a8)[0] != 0
    if connected and pending:
        raise PendingRoomOperation('observe pending completion before preparing disconnect')
    argument = None
    if connected:
        argument = struct.pack('<II', struct.unpack_from('<I', room_image, 0x39c)[0],
                               struct.unpack_from('<I', room_image, 0xc0)[0])
    image = bytearray(room_image)
    for offset, size in ((0xa0, 32), (0xd0, 16), (0xf4, 256), (0xc0, 12),
                         (0x1f4, 4), (0xe2, 2), (0xec, 2), (0x1f8, 2),
                         (0xe6, 2), (0xe8, 4), (0xf0, 4)):
        image[offset:offset+size] = bytes(size)
    struct.pack_into('<I', image, 0xcc, 0x21)
    struct.pack_into('<H', image, 0xe0, 2)
    image[0xe4] = 1
    tracked = connected and wait_for_completion
    return RoomDisconnectPreparation(bytes(image), argument, tracked, None if tracked else 0)
