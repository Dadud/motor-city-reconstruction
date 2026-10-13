"""Compare native cache resolution with the original-oracle synthetic corpus."""
import argparse
import struct
import subprocess
from client.part_type_templates import resolve_part_type_cache
from tools.part_type_cache_oracle import synthetic_cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', help='built mco_part_type_cache_compare executable')
    args = parser.parse_args()
    matched = 0
    for index, records in enumerate(synthetic_cases()):
        result = subprocess.run([args.executable], input=struct.pack('<I', len(records)) + b''.join(records),
                                capture_output=True, check=True, timeout=10)
        if result.stdout != b''.join(resolve_part_type_cache(records)):
            raise RuntimeError(f'native cache resolution differs in case {index}')
        matched += 1
    print(f'{matched} native/Python cache resolution cases match every byte; '
          'database loading and complete vehicle assembly remain separate checks.')


if __name__ == '__main__':
    main()
