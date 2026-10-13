"""Asset-free native/Python ordering comparison using the original-oracle corpus."""
import argparse
import struct
import subprocess

from client.owned_ordering import order_owned_candidates, reorder_owned_parts
from tools.owned_ordering_oracle import synthetic_cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', help='built mco_owned_ordering_compare executable')
    args = parser.parse_args()
    matched = 0
    for index, (slots, cache) in enumerate(synthetic_cases()):
        candidates = order_owned_candidates(slots, cache)
        reordered = reorder_owned_parts(slots, cache)
        wire = struct.pack('<II', len(slots), len(cache)) + b''.join(slots) + b''.join(cache)
        result = subprocess.run([args.executable], input=wire, capture_output=True,
                                check=True, timeout=10)
        expected = struct.pack('<I', len(candidates)) + b''.join(candidates) + b''.join(reordered)
        if result.stdout != expected:
            raise RuntimeError(f'native ordering candidates or count gate differ in case {index}')
        matched += 1
    print(f'{matched} candidate and reordered outputs match Python byte-for-byte including counts; '
          'full assembly loading and live gameplay remain separate checks.')


if __name__ == '__main__':
    main()
