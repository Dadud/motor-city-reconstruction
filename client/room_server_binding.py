"""Private connection-result image writes recovered from game task zero.

The embedded room begins at main owner +0xa0. Its server selector is the
successful local connection-interface return, never the configured shard ID.
Helper effects, authentication and socket ownership remain external boundaries.
"""
from dataclasses import dataclass
import struct

NETWORK_OWNER_MIN_SIZE = 0x6e0
EMBEDDED_ROOM_OFFSET = 0xa0


@dataclass(frozen=True)
class ServerBindingTransition:
    owner_image: bytes
    return_code: int
    mini_room_list_requested: bool
    notification: tuple[int, int] | None


def apply_server_connection_result(owner_image: bytes, native_result: int) -> ServerBindingTransition:
    """Dispatcher state writes, with success helpers represented as intents.

    Negative results preserve the old room selector and connected flag exactly.
    Success also preserves any prior error; no invented reset is performed.
    The image includes inert pointer tokens and is not a portable gameplay API.
    """
    if not isinstance(owner_image, bytes) or len(owner_image) < NETWORK_OWNER_MIN_SIZE:
        raise ValueError('expected complete game network owner image')
    if type(native_result) is not int or not -0x80000000 <= native_result <= 0x7fffffff:
        raise ValueError('native connection result must be int32')
    image = bytearray(owner_image)
    struct.pack_into('<i', image, 0x5cc, native_result)
    struct.pack_into('<I', image, 0x600, 0)
    if native_result < 0:
        struct.pack_into('<i', image, 0x5f4, native_result)
        return ServerBindingTransition(bytes(image), native_result, False, None)
    struct.pack_into('<I', image, EMBEDDED_ROOM_OFFSET + 0x39c, native_result)
    struct.pack_into('<I', image, 0x5fc, 1)
    return ServerBindingTransition(bytes(image), native_result, True, (native_result, 0))
