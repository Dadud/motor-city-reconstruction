"""Native 0x427d80 track-state template copy."""

# Exact 62-dword source image at mcity.exe:0x83b830, copied to 0x0097c238.
TRACK_TEMPLATE_BYTES = bytes.fromhex(
    '0000000000000000cdcccc3c6f12833c0ad7a33d8fc2f53c'
    '8fc2f53c0ad7a33ccdcccc3c6f12833c0ad7a33d0ad7233c'
    '9a99193e8fc2f53ccdcc4c3d0ad7a33c0000000000000000'
    '8fc2f53c8fc2f53ccdcccc3c6f12833ccdcccc3c6f12833c'
    'cdcc4c3d0ad7a33c0ad7a33d8fc2f53c0000000000000000'
    '0ad7233d8fc2f53c8fc2f53c8fc2f53ccdcc4c3e9a99193e'
    'cdcccc3d8fc2753d9a99193ecdcc4c3dcdcccc3c6f12833c'
    '8fc2f53c6f12833c8fc2f53c8fc2753dcdcccc3c0ad7233d'
    '8fc2753c6f12833c0000000000000000cdcccc3c6f12833c'
    'cdcccc3c6f12833c8fc2f53c0ad7a33c8fc2f53c0ad7a33c'
    'cdcccc3c6f12833c'
)
TRACK_TEMPLATE_DESTINATION = 0x0097c238


def initialize_track_template(destination):
    """Copy the observed 248-byte image into a writable native-state view."""
    if not isinstance(destination, bytearray):
        raise TypeError('track template destination must be a bytearray')
    if len(destination) < len(TRACK_TEMPLATE_BYTES):
        raise ValueError('track template destination is shorter than 248 bytes')
    destination[:len(TRACK_TEMPLATE_BYTES)] = TRACK_TEMPLATE_BYTES
    return destination
