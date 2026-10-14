"""Bounded original disconnect results and communication socket ownership guard.

These helpers perform no registry removal, reference release or socket action.
"""
import struct


def native_disconnect_result(removal_result):
    """73e2a0 converts zero removal result to -20, any nonzero result to zero."""
    if type(removal_result) is not int or not 0 <= removal_result <= 0xffffffff:
        raise ValueError('removal result must be a uint32')
    return 0 if removal_result else -20


def communication_socket_close_required(image):
    """743e40 ownership predicate; field names beyond channel ID remain opaque."""
    if not isinstance(image, bytes) or len(image) < 0x1a0:
        raise ValueError('communication image must contain at least 0x1a0 bytes')
    channel_id = struct.unpack_from('<I', image, 8)[0]
    flag194 = struct.unpack_from('<I', image, 0x194)[0]
    flag19c = struct.unpack_from('<I', image, 0x19c)[0]
    return flag194 != 0 and (channel_id == 0 or flag19c != 0)
