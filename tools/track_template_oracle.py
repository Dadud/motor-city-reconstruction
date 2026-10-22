"""Compare the 0x427d80 static track-template copy with mcity.exe."""
import argparse
import json

from client.track_template import (
    TRACK_TEMPLATE_BYTES, TRACK_TEMPLATE_DESTINATION, initialize_track_template,
)
from tools.native_oracle import DynoOracle


TRACK_TEMPLATE_SOURCE = 0x0083b830


def compare(executable):
    oracle = DynoOracle(executable)
    source = bytes(oracle.cpu.mem_read(TRACK_TEMPLATE_SOURCE,
                                      len(TRACK_TEMPLATE_BYTES)))
    if source != TRACK_TEMPLATE_BYTES:
        raise AssertionError('authored track template differs from pinned executable bytes')

    destination = bytearray(len(TRACK_TEMPLATE_BYTES))
    initialize_track_template(destination)
    oracle.call(0x427d80, instruction_limit=2_000)
    native = bytes(oracle.cpu.mem_read(TRACK_TEMPLATE_DESTINATION,
                                      len(TRACK_TEMPLATE_BYTES)))
    if native != destination:
        offset = next(i for i, (actual, wanted) in enumerate(zip(native, destination))
                      if actual != wanted)
        raise AssertionError(f'copy differs at destination +{offset:#x}')
    return {
        'entry': '0x427d80',
        'source': hex(TRACK_TEMPLATE_SOURCE),
        'destination': hex(TRACK_TEMPLATE_DESTINATION),
        'bytes_matched': len(native),
        'source_and_destination_match': True,
        'scope': 'original function emulated with its static source image; '
                 'no Windows process, allocator or game-loop behavior is included',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    args = parser.parse_args()
    print(json.dumps(compare(args.executable)))
