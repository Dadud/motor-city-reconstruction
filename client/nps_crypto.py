"""Recovered SHA-1 mask expansion from the legacy login session path.

0x7c7cb0 hashes seed plus a big-endian uint32 counter starting at zero.
0x7b69b0 selects big-endian counter bytes; 0x7d22a0/0x7d22e0 identify SHA-1.
This module does not yet implement the complete session encryption operation.
"""
import hashlib
import struct


def mask_sha1(seed, length):
    """MGF1-style mask bytes; caller combines them with its destination.

    Bound to the recovered login string capacity, not a general crypto API.
    """
    if not isinstance(seed, bytes):
        raise TypeError('mask seed must be bytes')
    if len(seed) > 512:
        raise ValueError('mask seed exceeds supported login size')
    if type(length) is not int or not 0 <= length <= 512:
        raise ValueError('mask length must be within [0, 512]')
    return b''.join(hashlib.sha1(seed + struct.pack('>I', counter)).digest()
                    for counter in range((length + 19)//20))[:length]
