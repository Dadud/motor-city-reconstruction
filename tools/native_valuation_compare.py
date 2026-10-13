"""Compare the native port with the recovered Python calculation, asset-free."""
import argparse
import random
import struct
import subprocess
from client.owned_valuation import PartValuationRates, calculate_owned_valuation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', help='built mco_valuation_compare executable')
    args = parser.parse_args()
    rng = random.Random(6617)
    slots = []
    for index in range(512):
        slot = bytearray(1596)
        struct.pack_into('<I', slot, 0, rng.choice([160001, 20000, 20001, 20999, 21000]))
        struct.pack_into('<I', slot, 0x1e3, 123)
        struct.pack_into('<ii', slot, 0x1eb, rng.randint(-100000, 10000000), rng.choice([0, 1, 1000, 200000]))
        struct.pack_into('<f', slot, 0x454, rng.uniform(-10000, 10000))
        struct.pack_into('<I', slot, 0x5f8, 0 if index % 31 == 0 else 42)
        struct.pack_into('<ii', slot, 0x610, rng.randint(-100, 1000), rng.randint(-1000, 100000))
        slots.append(bytes(slot))
    result = subprocess.run([args.executable], input=b''.join(slots), capture_output=True, check=True, timeout=30)
    lines = result.stdout.decode('ascii').splitlines()
    if len(lines) != len(slots):
        raise RuntimeError('native output record count differs')
    rates = PartValuationRates(0.1, 0.75)
    for index, (slot, line) in enumerate(zip(slots, lines)):
        expected = calculate_owned_valuation(slot, rates)
        if expected is None:
            if line != 'empty':
                raise RuntimeError(f'identity mismatch at case {index}')
        else:
            repair, scrap, condition = line.split()
            actual = (int(repair), int(scrap), float.fromhex(condition))
            if actual != (expected.repair_cost, expected.scrap_value, expected.wear_condition):
                raise RuntimeError(f'valuation mismatch at case {index}: {actual} != {expected}')
    print(f'{len(slots)} native/Python valuation comparisons passed; not a full-game parity claim.')


if __name__ == '__main__':
    main()
