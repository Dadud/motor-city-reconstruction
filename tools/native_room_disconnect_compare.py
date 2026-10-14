"""Asset-free native/Python stable disconnect images and initialized arguments."""
import argparse
import random
import struct
import subprocess

from client.room_disconnect import prepare_room_disconnect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', help='built mco_room_disconnect_compare executable')
    args = parser.parse_args()
    rng = random.Random(0x44d750)
    matched = 0
    for status in (0, 1, 0xffff):
        for wait in (False, True):
            for extra in range(16):
                source = bytearray(rng.randbytes(0x3c0 + extra))
                struct.pack_into('<H', source, 0xec, status)
                struct.pack_into('<I', source, 0x3a8, rng.getrandbits(32) if not status else 0)
                image = bytes(source)
                expected = prepare_room_disconnect(image, wait_for_completion=wait)
                wire = struct.pack('<II', len(image), wait) + image
                actual = subprocess.run([args.executable], input=wire, capture_output=True,
                                        check=True, timeout=10)
                expected_wire = (struct.pack('<7I', expected.argument is not None, expected.task_kind or 0,
                                             expected.tracked, expected.immediate_return is not None,
                                             expected.immediate_return or 0, *expected.reset_owner_offsets)
                                 + (expected.argument or b'') + expected.room_image)
                if actual.stdout != expected_wire:
                    raise RuntimeError(f'native disconnect preparation differs in case {matched}')
                matched += 1
    print(f'{matched} native/Python stable disconnect preparations match byte-for-byte; '
          'pending waits, enqueue effects and live disconnection remain separate checks.')


if __name__ == '__main__':
    main()
