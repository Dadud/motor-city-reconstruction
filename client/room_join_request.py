"""Private room-argument producer recovered from original 0x44cf80.

These are native-layout research images, not ready-to-send network packets or a
stable mod API. Owner tokens and the original cancellation address remain opaque
data; this module never invokes them or schedules tasks.
"""
from dataclasses import dataclass, field
import struct

from client.lobby_channel_record import CHANNEL_ARGUMENT_SIZE

_ORIGINAL_CANCEL_CALLBACK = 0x44d740


def _integer(value, bits, label):
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise ValueError(f'{label} must fit uint{bits}')
    return value


@dataclass(frozen=True)
class RoomJoinInputs:
    server_selector: int
    protocol: int
    channel_id: int
    name: bytes
    max_ready: int
    opaque_data: bytes = field(repr=False)

    def __post_init__(self):
        for label in ('server_selector', 'protocol', 'channel_id'):
            _integer(getattr(self, label), 32, label)
        _integer(self.max_ready, 16, 'max_ready')
        if not isinstance(self.name, bytes) or len(self.name) > 31 or b'\0' in self.name:
            raise ValueError('room name must contain at most 31 bytes without NUL')
        if not isinstance(self.opaque_data, bytes) or len(self.opaque_data) != 256:
            raise ValueError('expected exactly 256 opaque room bytes')

    @classmethod
    def from_room_image(cls, image):
        """Extract only observed inputs; unknown room-object fields stay private."""
        if not isinstance(image, bytes) or not 0x3a0 <= len(image) <= 65536:
            raise ValueError('expected bounded room image covering offset 0x39f')
        name = image[0xa0:0xc0]
        end = name.find(b'\0')
        if end < 0:
            raise ValueError('room image name requires NUL within its 32-byte field')
        return cls(struct.unpack_from('<I', image, 0x39c)[0],
                   struct.unpack_from('<I', image, 0xcc)[0],
                   struct.unpack_from('<I', image, 0xc0)[0], name[:end],
                   struct.unpack_from('<H', image, 0xe6)[0], image[0xf4:0x1f4])


def build_room_join_argument(inputs, *, password=None, flag_0x20=False,
                             wait_for_completion=False, owner_token=None):
    """Reproduce the producer's initialized argument, within safe string bounds.

    The original copies strings without local bounds. This reconstruction
    requires a password of at most 16 bytes, so the downstream 17-byte copied
    password field contains its NUL. It intentionally does not reproduce an
    overflow or infer allocation-tail termination.
    """
    if not isinstance(inputs, RoomJoinInputs):
        raise TypeError('expected RoomJoinInputs')
    if type(flag_0x20) is not bool or type(wait_for_completion) is not bool:
        raise TypeError('producer switches must be boolean')
    if password is not None and (not isinstance(password, bytes) or len(password) > 16 or b'\0' in password):
        raise ValueError('password must contain at most 16 bytes without NUL')
    if wait_for_completion:
        _integer(owner_token, 32, 'explicit owner token')
    elif owner_token is not None:
        raise ValueError('owner token is used only for the waiting producer branch')
    password = password or b''
    image = bytearray(CHANNEL_ARGUMENT_SIZE)
    mode = 1 if password else 2
    flags = mode | (0x20 if flag_0x20 else 0)
    struct.pack_into('<4I', image, 0, inputs.server_selector, inputs.protocol, inputs.channel_id, flags)
    image[0x10:0x10 + len(inputs.name)] = inputs.name
    image[0x34:0x34 + len(password)] = password
    image[0x50:0x150] = inputs.opaque_data
    struct.pack_into('<HH', image, 0x150, inputs.max_ready, mode)
    if wait_for_completion:
        struct.pack_into('<II', image, 0x154, _ORIGINAL_CANCEL_CALLBACK, owner_token)
    return bytes(image)
