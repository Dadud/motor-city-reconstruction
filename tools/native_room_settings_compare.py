"""Asset-free native/Python room-settings full-image comparison."""
import argparse
import itertools
import random
import struct
import subprocess

from client.room_settings import ROOM_SETTINGS_MIN_SIZE, apply_room_settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', help='built mco_room_settings_compare executable')
    args = parser.parse_args()
    rng = random.Random(0x44db80)
    matched = 0
    for name_size, secondary_size, extra in itertools.product((0,1,29,30,31), (0,1,14,15), (0,1,17,64)):
        room = rng.randbytes(0x3c0 + extra)
        source = bytearray(rng.randbytes(ROOM_SETTINGS_MIN_SIZE + extra))
        source[:name_size + 1] = b'n' * name_size + b'\0'
        source[0x30:0x30 + secondary_size + 1] = b's' * secondary_size + b'\0'
        settings = bytes(source)
        wire = struct.pack('<II', len(room), len(settings)) + room + settings
        actual = subprocess.run([args.executable], input=wire, capture_output=True, check=True, timeout=10)
        if actual.stdout != apply_room_settings(room, settings):
            raise RuntimeError(f'native room settings differ at case {matched}')
        matched += 1
    print(f'{matched} native/Python room-settings images match byte-for-byte including string tails; '
          'authenticated settings selection and live rooms remain separate checks.')


if __name__ == '__main__':
    main()
