"""Original game authorization ID and executable checksum for NPS login.

Service literal at 0x8b7358 is supplied by 0x5eda30. Checksum setup 0x5240b0
reads the whole running executable; 0x658280 folds bytes with initial 0xffffffff
and the reflected CRC-32 table, without a final complement.
"""
from pathlib import Path
from .crc32 import crc32_raw

SERVICE_ID = '2176'
MAX_EXECUTABLE_BYTES = 32*1024*1024


def executable_checksum(data):
    if not isinstance(data, bytes):
        raise TypeError('executable data must be bytes')
    if len(data) > MAX_EXECUTABLE_BYTES:
        raise ValueError('executable exceeds supported size')
    return crc32_raw(data)


def installed_executable_checksum(root):
    """Checksum the user's external original mcity.exe, not the Python launcher.

    This reproduces the original identity value. Server acceptance of a rebuilt
    client using that identity still requires an authenticated test.
    """
    path = Path(root)/'mcity.exe'
    if path.stat().st_size > MAX_EXECUTABLE_BYTES:
        raise ValueError('executable exceeds supported size')
    return executable_checksum(path.read_bytes())
