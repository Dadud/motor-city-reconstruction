"""Asset-free outer-description parity; leaf/localization inputs are fixtures."""
import argparse
import struct
import subprocess
from client.owned_descriptions import apply_owned_descriptions
from tools.owned_descriptions_oracle import LABELS, leaf_fixture, synthetic_cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    args = parser.parse_args()
    matched = 0
    for case, (slots, cache) in enumerate(synthetic_cases()):
        expected = apply_owned_descriptions(slots, cache, attachment_labels=LABELS, leaf_description=leaf_fixture)
        result = subprocess.run([args.executable], input=struct.pack('<II', len(slots), len(cache)) +
                                b''.join(slots) + b''.join(cache), check=True, capture_output=True, timeout=10)
        if result.stdout != b''.join(expected):
            raise ValueError(f'native outer description differs in case {case}')
        matched += 1
    print(f'{matched} outer-description outputs match Python byte-for-byte; '
          'leaf rendering and localized labels remain explicit fixtures.')


if __name__ == '__main__':
    main()
