"""Fallback surface correction wrapper from original routine 0x43bfd0."""
import struct

from .tire_response import f32


def correct_surface_collision(record, track_index, *, vertical_step,
                              adjust_contact, reset_vehicle_state):
    """Run the wrapper around its two larger native child routines.

    ``adjust_contact`` corresponds to 0x43ba40 and may update the owner,
    including its status at +0x36c. The wrapper then adds either the configured
    vertical step or half of it to Y at +0x0c, and invokes the 0x43b750 state
    reset. The two child bodies remain explicit dependencies.
    """
    if not isinstance(record, bytearray) or len(record) < 0x4F8:
        raise ValueError('a mutable world-object record is required')
    if type(track_index) is not int or not 0 <= track_index <= 0xffffffff:
        raise ValueError('track index must be uint32')
    if not callable(adjust_contact) or not callable(reset_vehicle_state):
        raise ValueError('both original correction child routines are required')
    step = f32(vertical_step)
    adjust_contact(record, track_index)
    if struct.unpack_from('<i', record, 0x36C)[0] != 0:
        step = f32(step * f32(0.5))
    y = struct.unpack_from('<f', record, 0x0C)[0]
    struct.pack_into('<f', record, 0x0C, f32(step + y))
    reset_vehicle_state(record)
    return record
