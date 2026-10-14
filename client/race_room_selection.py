"""Recovered final race-room selection edits from original 0x5e4870.

Inputs are explicit local session/settings data, not guessed fan-server values.
The 204-byte metadata must already be produced by the original-equivalent
metadata builder; this module does not pretend to recover that whole builder.
"""
from dataclasses import dataclass, field
import struct

from client.room_join_request import RoomJoinInputs


def _uint32(value, label):
    if type(value) is not int or not 0 <= value <= 0xffffffff:
        raise ValueError(f'{label} must fit uint32')
    return value


def _string(value, maximum, label):
    if not isinstance(value, bytes) or len(value) > maximum or b'\0' in value:
        raise ValueError(f'{label} requires at most {maximum} bytes without NUL')
    return value


@dataclass(frozen=True)
class RaceRoomSelection:
    name: bytes
    channel_id: int
    max_ready: int
    password: bytes = field(repr=False)
    metadata: bytes = field(repr=False)

    def room_inputs(self, server_selector):
        """0x4509c0 defaults protocol to 0x21 and pads its data region to 256.

        The server selector is supplied from an authenticated connection binding;
        a configured shard number is not inferred to be that local selector.
        """
        return RoomJoinInputs(server_selector,0x21,self.channel_id,self.name,
                              self.max_ready,self.metadata + bytes(52))


def prepare_race_room_selection(metadata, *, game_mode, room_name, channel_id,
                                ready_value, password, value_0x78,
                                value_0x90, value_0xa8):
    """Reproduce the final caller edits and unsigned decimal name override.

    Metadata is snapshotted before name override, preserving the original order.
    Downstream safe name/password limits are explicit reconstruction boundaries.
    This function neither performs prior room validation nor disconnects/joins.
    """
    if not isinstance(metadata, bytes) or len(metadata) != 0xcc:
        raise ValueError('expected exactly 204 prepared metadata bytes')
    game_mode = _uint32(game_mode,'game mode')
    channel_id = _uint32(channel_id,'channel ID')
    ready_value = _uint32(ready_value,'ready source value')
    for value,label in ((value_0x78,'value_0x78'),(value_0x90,'value_0x90'),(value_0xa8,'value_0xa8')):
        _uint32(value,label)
    room_name = _string(room_name,31,'room name')
    password = _string(password,16,'room password')
    patched = bytearray(metadata)
    patched[0x64] &= 0xe1
    for offset,value in ((0x78,value_0x78),(0x90,value_0x90),(0xa8,value_0xa8)):
        struct.pack_into('<I',patched,offset,value)
    if game_mode in (0x13,0x19) and channel_id != 0:
        room_name = str(channel_id).encode('ascii')
    return RaceRoomSelection(room_name,channel_id,ready_value & 0xffff,password,bytes(patched))
