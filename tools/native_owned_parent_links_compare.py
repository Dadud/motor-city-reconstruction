"""Asset-free native/Python comparison using the original-oracle case corpus."""
import argparse
import struct
import subprocess
from client.owned_parent_links import select_owned_root, link_owned_parents
from tools.owned_parent_links_oracle import synthetic_cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', help='built mco_owned_parent_links_compare executable')
    args = parser.parse_args()
    matched = 0
    for index, (slots, templates) in enumerate(synthetic_cases()):
        selected, status = select_owned_root(slots, templates)
        parents = link_owned_parents(slots, templates)
        wire = struct.pack('<II', len(slots), len(templates)) + b''.join(slots) + b''.join(templates)
        result = subprocess.run([args.executable], input=wire, capture_output=True, check=True, timeout=10)
        expected = struct.pack('<i', status) + b''.join(selected) + b''.join(parents)
        if result.stdout != expected:
            raise RuntimeError(f'native root/parent output differs in case {index}')
        matched += 1
    print(f'{matched} root and {matched} parent/family outputs match Python byte-for-byte; '
          'full assembly and live gameplay remain separate checks.')


if __name__ == '__main__':
    main()
