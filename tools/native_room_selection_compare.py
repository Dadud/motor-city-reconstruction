"""Asset-free native/Python settings initialization and room selection parity."""
import argparse
import itertools
import random
import struct
import subprocess

from client.room_selection import initialize_room_settings, select_room


def run(executable, wire, expected, label):
    actual = subprocess.run([executable], input=wire, capture_output=True, check=True, timeout=10)
    if actual.stdout != expected:
        raise RuntimeError(f'native room selection differs: {label}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', help='built mco_room_selection_compare executable')
    args = parser.parse_args()
    rng = random.Random(0x450830)
    initialized = selected = 0
    for size, repeat in itertools.product((0x15a, 0x160, 0x171, 1024, 4096, 65536), range(4)):
        image = rng.randbytes(size)
        run(args.executable, struct.pack('<II', 0, size) + image, initialize_room_settings(image), f'init{size}/{repeat}')
        initialized += 1
    for connected, pending, name, use_cache in itertools.product((0,1,0xffff), (0,1),
                (b'old',b'OLD',b'new',b'',b'n'*31,b'\xff\xfe'), (False,True)):
        room = bytearray(rng.randbytes(0x3c0 + selected % 17))
        room[0xa0:0xa4] = b'old\0'
        struct.pack_into('<H', room, 0xec, connected)
        struct.pack_into('<I', room, 0x3a8, pending)
        cache = None
        if use_cache:
            if connected or pending:
                cache = b'invalid unused cache'
            else:
                cached = bytearray(rng.randbytes(0x15a + selected % 9))
                cached[:7] = b'cached\0'
                cached[0x30:0x32] = b's\0'
                struct.pack_into('<HH', cached, 0x46, 77, 0xabcd)
                struct.pack_into('<H', cached, 0x4c, 99)
                cache = bytes(cached)
        source = bytes(room)
        expected = select_room(source, name, cached_settings=cache)
        cache_bytes = cache or b''
        wire = (struct.pack('<5I', 1, len(source), len(name), cache is not None, len(cache_bytes))
                + source + name + cache_bytes)
        expected_wire = struct.pack('<iI', expected.result, {'active':0,'defaults':1,'cache':2}[expected.source]) + expected.room_image
        run(args.executable, wire, expected_wire, f'select{selected}')
        selected += 1
    print(f'{initialized} initializers and {selected} native/Python room selections match full images and results; '
          'live cache lookup and authenticated room entry remain separate checks.')


if __name__ == '__main__':
    main()
