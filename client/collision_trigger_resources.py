"""TRxx.CAN world-trigger resource decoding from 0x407570."""
from dataclasses import dataclass
import struct

from client.tire_response import f32


_HEADER_SIZE = 8
_RECORD_SIZE = 0x14
_COORD_SCALE = f32(0.7692308)
_FIXED_16_SCALE = f32(1.5258789e-5)
_WORLD_SCALE = f32(65536.0)


@dataclass(frozen=True)
class CollisionTriggerArchive:
    header: bytes
    records: tuple[bytes, ...]

    def encode(self):
        return self.header + b''.join(self.records)


@dataclass(frozen=True)
class LoadedCollisionTriggerArchives:
    resources: tuple[bytes | None, ...]
    loaded_count: int


def decode_collision_trigger_archive(data):
    """Read the 8-byte header and count 20-byte records of a TRxx.CAN file."""
    data = bytes(data)
    if len(data) < _HEADER_SIZE:
        raise ValueError('trigger archive is shorter than its 8-byte header')
    count = struct.unpack_from('<H', data, 4)[0]
    expected_size = _HEADER_SIZE + count * _RECORD_SIZE
    if len(data) != expected_size:
        raise ValueError(
            f'trigger archive size {len(data)} does not match count {count} '
            f'and record size {_RECORD_SIZE}')
    return CollisionTriggerArchive(
        data[:_HEADER_SIZE],
        tuple(data[offset:offset + _RECORD_SIZE]
              for offset in range(_HEADER_SIZE, expected_size, _RECORD_SIZE)))


def _convert_coordinate(value, axis):
    # 0x407570 uses x87 double-precision intermediates, but spills Y/Z to
    # float32 before their final 65536 scale. X is spilled after that scale.
    value = float(value) * _FIXED_16_SCALE
    value *= _COORD_SCALE
    if axis == 0:
        value *= _WORLD_SCALE
        value = f32(value)
    else:
        value = f32(value)
        value *= _WORLD_SCALE
    return int(round(value))


def normalize_collision_trigger_archive(data):
    """Apply the loader's 0.7692308 coordinate conversion to record XYZ."""
    archive = decode_collision_trigger_archive(data)
    records = []
    for record in archive.records:
        converted = bytearray(record)
        for axis, offset in enumerate((0, 4, 8)):
            value = struct.unpack_from('<i', record, offset)[0]
            struct.pack_into('<i', converted, offset,
                             _convert_coordinate(value, axis))
        records.append(bytes(converted))
    return CollisionTriggerArchive(archive.header, tuple(records))


def load_collision_trigger_archives(archives):
    """Model the seven-slot load order: TR00A.CAN, then TR01.CAN through TR06.CAN.

    Missing input stops the original loader at that slot. Malformed present
    data is rejected by this decoder. Inputs after the first missing slot are
    not inspected.
    """
    archives = tuple(archives)
    if len(archives) != 7:
        raise ValueError('exactly seven ordered archive inputs are required')
    resources = []
    loaded_count = 0
    for data in archives:
        if data is None:
            resources.append(None)
            resources.extend([None] * (7 - len(resources)))
            break
        normalized = normalize_collision_trigger_archive(data).encode()
        resources.append(normalized)
        loaded_count += 1
    return LoadedCollisionTriggerArchives(tuple(resources), loaded_count)
