"""Publish the mapped mouse-button snapshot used by 0x4ad6f0."""
from dataclasses import dataclass


@dataclass(frozen=True)
class MouseMappingSource:
    """The 0x13-byte state returned by mouse getter selector six."""

    device_state: bytes
    mapped_9abb20: int
    mapped_9abb24: int
    mapped_9abb1c: int
    mapped_9abb28: int


@dataclass(frozen=True)
class MouseMappingSnapshot:
    """Globals consumed by action predicates and directional transitions."""

    value_9e1654: int
    value_9e1648: int
    value_9e1658: int
    value_9e164c: int
    value_9e165c: int
    value_9e1668: int
    value_9e1650: int


def publish_mouse_mapping_snapshot(source):
    """Port 0x4ad869..0x4ad8c5 without carrying device access into the core.

    The original normalizes bytes +0x10..+0x12 to uint32 Boolean globals and
    copies four existing mapping words into their separate destinations. The
    selector-six device getter remains the caller's acquisition boundary.
    """
    if not isinstance(source, MouseMappingSource):
        raise ValueError('MouseMappingSource is required')
    if not isinstance(source.device_state, (bytes, bytearray, memoryview)) \
            or len(source.device_state) < 0x13:
        raise ValueError('mouse state must expose button bytes through offset 0x12')
    values = (source.mapped_9abb20, source.mapped_9abb24,
              source.mapped_9abb1c, source.mapped_9abb28)
    if any(type(value) is not int or not 0 <= value <= 0xffffffff for value in values):
        raise ValueError('mapped action values must be uint32')
    flags = source.device_state
    return MouseMappingSnapshot(
        value_9e1654=int(flags[0x10] != 0),
        value_9e1648=source.mapped_9abb20,
        value_9e1658=int(flags[0x11] != 0),
        value_9e164c=source.mapped_9abb24,
        value_9e165c=int(flags[0x12] != 0),
        value_9e1668=source.mapped_9abb1c,
        value_9e1650=source.mapped_9abb28)
