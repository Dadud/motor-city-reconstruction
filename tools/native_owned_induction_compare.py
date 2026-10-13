"""Compare native induction pruning with the original-oracle case corpus."""
import argparse
import struct
import subprocess
from client.owned_induction import prune_owned_induction_placeholders
from tools.owned_induction_oracle import synthetic_cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', help='built mco_owned_induction_compare executable')
    args = parser.parse_args()
    matched = 0
    for index, slots in enumerate(synthetic_cases()):
        result = subprocess.run([args.executable], input=struct.pack('<I', len(slots)) + b''.join(slots),
                                capture_output=True, check=True, timeout=10)
        expected = prune_owned_induction_placeholders(slots)
        if result.stdout != struct.pack('<I', len(expected)) + b''.join(expected):
            raise RuntimeError(f'native induction pruning differs in case {index}')
        matched += 1
    print(f'{matched} native/Python induction pruning cases match count and every retained byte; '
          'earlier missing-part insertion remains a separate check.')


if __name__ == '__main__':
    main()
