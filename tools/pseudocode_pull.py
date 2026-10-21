"""Pull exported decompiler pseudocode into the cell workflow.

The private export carries one C file per function for every routine the
static pass decompiled. Reading it turns the slowest step of a recovery cell -
deriving semantics from disassembly - into reading C.

Two caveats keep this honest. Pseudocode is a provider-specific reconstruction;
verify signatures against call sites and epilogues. For 0x483450, both Ghidra's
parameter use and the direct call site establish two cdecl arguments. And
pseudocode is a draft for the implementation, never the verification: the
oracle against the original remains the only judge.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / 'evidence' / 'recovery-export'
CLIENT = '28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164'


def pseudocode_path(address, digest=CLIENT):
    """Locate one exported C file by routine address."""
    offset = int(address, 16)
    path = EXPORT/digest/'pseudocode'/f'{offset:08x}.c'
    return path if path.is_file() else None


def read_pseudocode(address, digest=CLIENT):
    path = pseudocode_path(address, digest)
    if path is None:
        raise ValueError(f'no exported pseudocode for {address}')
    return path.read_text(encoding='utf-8', errors='replace')


def pull(addresses, digest=CLIENT):
    result = {}
    missing = []
    for address in addresses:
        try:
            result[address] = read_pseudocode(address, digest)
        except ValueError:
            missing.append(address)
    return result, missing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('addresses', nargs='+', help='routine addresses, e.g. 0x405df0')
    parser.add_argument('--digest', default=CLIENT)
    parser.add_argument('--missing', action='store_true',
                        help='list addresses without exported pseudocode')
    args = parser.parse_args()
    found, missing = pull(args.addresses, args.digest)
    if args.missing:
        print(json.dumps(dict(found=sorted(found), missing=missing)))
        return
    if missing:
        print(f'no pseudocode for: {", ".join(missing)}', file=sys.stderr)
    for address, code in found.items():
        print(f'=== {address} ===\n{code}')


if __name__ == '__main__':
    main()
