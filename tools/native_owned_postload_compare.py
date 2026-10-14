"""Asset-free postload comparison; descriptions remain an authored fixture."""
import argparse
import struct
import subprocess
from client.owned_postload import postprocess_owned_slots
from tools.owned_postload_oracle import synthetic_cases, description_fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    args = parser.parse_args()
    matched = 0
    for case, (slots, cache, options) in enumerate(synthetic_cases()):
        expected = postprocess_owned_slots(slots, cache, description_pass=description_fixture, **options)
        header = (len(slots), len(cache), int(options['finalize_enabled']),
                  options['finalize_mode'], options['display_mode'],
                  int(options['reorder']), int(options['enriched']))
        result = subprocess.run([args.executable], input=struct.pack('<7I', *header) +
                                b''.join(slots) + b''.join(cache), capture_output=True,
                                check=True, timeout=10)
        if result.stdout != struct.pack('<I', len(expected)) + b''.join(expected):
            raise ValueError(f'native postload differs in case {case}')
        matched += 1
    print(f'{matched} postload outputs match Python byte-for-byte with explicit description fixtures; '
          'original descriptions and complete loading remain unverified.')


if __name__ == '__main__':
    main()
