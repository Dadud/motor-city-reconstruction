"""Asset-free native/Python insertion comparison using the original-oracle corpus."""
import argparse
import struct
import subprocess

from client.owned_insertion import insert_owned_placeholders
from tools.owned_insertion_oracle import synthetic_cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', help='built mco_owned_insertion_compare executable')
    args = parser.parse_args()
    matched = 0
    for index, (slots, templates, mode) in enumerate(synthetic_cases()):
        output = insert_owned_placeholders(slots, templates, display_mode=mode)
        wire = (struct.pack('<III', len(slots), len(templates), mode)
                + b''.join(slots) + b''.join(templates))
        result = subprocess.run([args.executable], input=wire, capture_output=True,
                                check=True, timeout=10)
        expected = struct.pack('<I', len(output)) + b''.join(output)
        if result.stdout != expected:
            raise RuntimeError(f'native insertion output differs in case {index}, mode {mode}')
        matched += 1
    print(f'{matched} insertion outputs match Python byte-for-byte including counts and display modes; '
          'full finalization and live gameplay remain separate checks.')


if __name__ == '__main__':
    main()
