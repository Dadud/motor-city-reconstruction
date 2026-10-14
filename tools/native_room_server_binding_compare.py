"""Asset-free native/Python server-binding image and helper-intent comparison."""
import argparse
import random
import struct
import subprocess

from client.room_server_binding import NETWORK_OWNER_MIN_SIZE, apply_server_connection_result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', help='built mco_room_server_binding_compare executable')
    args = parser.parse_args()
    rng = random.Random(0x454d50)
    count = 0
    for result in (-0x80000000, -59, -51, -6, -1, 0, 1, 7, 44, 0x7fffffff):
        for extra in (0, 1, 7, 23, 64, 100, 256, 1024):
            original = rng.randbytes(NETWORK_OWNER_MIN_SIZE + extra)
            expected = apply_server_connection_result(original, result)
            note = expected.notification or (0, 0)
            expected_wire = (struct.pack('<iIIII', expected.return_code,
                                         expected.mini_room_list_requested,
                                         expected.notification is not None, *note)
                             + expected.owner_image)
            wire = struct.pack('<Ii', len(original), result) + original
            actual = subprocess.run([args.executable], input=wire, capture_output=True,
                                    check=True, timeout=10)
            if actual.stdout != expected_wire:
                raise RuntimeError(f'native server binding differs for result {result}, extra {extra}')
            count += 1
    print(f'{count} native/Python full-image, signed-return and helper-intent comparisons passed; '
          'authentication and live connection ownership remain separate checks.')


if __name__ == '__main__':
    main()
