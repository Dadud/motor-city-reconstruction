"""Recovered channel-close arguments and plain opcode 0x105 packet.

The server selector is local registry routing data, not a serialized field.
This module opens no socket and neither removes local state nor performs logoff.
"""
from dataclasses import dataclass
import struct

from client.nps_framing import Frame


def native_close_arguments(server_selector, channel_id):
    """Initialized local pair passed through room task 1, little endian."""
    for value in (server_selector, channel_id):
        if type(value) is not int or not 0 <= value <= 0xffffffff:
            raise ValueError('channel-close arguments must fit uint32')
    return struct.pack('<II', server_selector, channel_id)


@dataclass(frozen=True)
class ChannelCloseRequest:
    channel_id: int

    def __post_init__(self):
        if type(self.channel_id) is not int or not 0 <= self.channel_id <= 0xffffffff:
            raise ValueError('channel-close field must fit uint32')

    def payload(self):
        return struct.pack('>I', self.channel_id)

    def frame(self):
        return Frame(0x105, self.payload())
