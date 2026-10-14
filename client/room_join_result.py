"""Private room worker call/result boundary recovered from 0x44eba0.

Offsets are relative to that function's ECX base, not the worker interface at
base+12. Pure image transformations exclude logging and helper side effects.
"""
from dataclasses import dataclass
import struct

from client.lobby_channel_record import CHANNEL_ARGUMENT_SIZE

ROOM_WORKER_MIN_SIZE = 0x3b8


def _image(value):
    if not isinstance(value, bytes) or len(value) < ROOM_WORKER_MIN_SIZE:
        raise ValueError('expected complete room worker image')
    return value


@dataclass(frozen=True)
class RoomJoinCall:
    interface_token: int
    argument: bytes
    caller_value_1: int
    caller_value_2: int


def room_join_call(worker_image: bytes, argument: bytes) -> RoomJoinCall:
    """Values forwarded to interface entry +8; never dereference its token."""
    _image(worker_image)
    if not isinstance(argument, bytes) or len(argument) != CHANNEL_ARGUMENT_SIZE:
        raise ValueError('expected exact native room argument')
    first, second, interface = struct.unpack_from('<3I', worker_image, 0x3ac)
    return RoomJoinCall(interface, argument, first, second)


@dataclass(frozen=True)
class RoomJoinNotification:
    owner_offset: int
    correlation_value: int
    channel_value: int


@dataclass(frozen=True)
class RoomJoinTransition:
    worker_image: bytes
    return_code: int
    notification: RoomJoinNotification | None


def apply_room_join_result(worker_image: bytes, native_result: int) -> RoomJoinTransition:
    """Writes before substituted helper 0x456ae0, preserving all other bytes.

    Nonnegative values become the retained channel value and return zero.
    Negative values become the retained error and return unchanged. This does
    not infer a wire transaction ID, enqueue tasks or establish a live room join.
    """
    _image(worker_image)
    if type(native_result) is not int or not -0x80000000 <= native_result <= 0x7fffffff:
        raise ValueError('native room result must be int32')
    image = bytearray(worker_image)
    struct.pack_into('<I', image, 0x3a8, 0)
    if native_result < 0:
        struct.pack_into('<i', image, 0x3a4, native_result)
        return RoomJoinTransition(bytes(image), native_result, None)
    struct.pack_into('<H', image, 0xec, 1)
    struct.pack_into('<I', image, 0xc0, native_result)
    correlation = struct.unpack_from('<I', image, 0x39c)[0]
    notification = RoomJoinNotification(0x1fc, correlation, native_result)
    return RoomJoinTransition(bytes(image), 0, notification)
