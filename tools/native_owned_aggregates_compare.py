"""Asset-free native/Python aggregation comparison using the original-oracle corpus."""
import argparse
import struct
import subprocess

from client.owned_aggregates import (apply_owned_component_counts,
                                     apply_owned_repair_scrap_aggregates,
                                     apply_owned_total_price)
from tools.owned_aggregates_oracle import synthetic_cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', help='built mco_owned_aggregates_compare executable')
    args = parser.parse_args()
    matched = 0
    for index, slots in enumerate(synthetic_cases()):
        expected = (b''.join(apply_owned_component_counts(slots))
                    + b''.join(apply_owned_repair_scrap_aggregates(slots))
                    + b''.join(apply_owned_total_price(slots)))
        wire = struct.pack('<I', len(slots)) + b''.join(slots)
        result = subprocess.run([args.executable], input=wire, capture_output=True,
                                check=True, timeout=10)
        if result.stdout != expected:
            raise RuntimeError(f'native count/cost/price aggregation differs in case {index}')
        matched += 1
    print(f'{matched} cases each of counts, repair/scrap, and total price match Python byte-for-byte; '
          'full mechanical aggregation and live transactions remain separate checks.')


if __name__ == '__main__':
    main()
