"""Compare the bounded Python 0x42e760 port with 1,200 original calls."""
from pathlib import Path

from client.track_surface_lookup import (TrackSurfaceMemory, TrackSurfaceWorld,
                                         track_surface_lookup)
from tools.native_oracle import DynoOracle
from tools.track_surface_cases import (BASE, BLOCKS, PATH, capture,
                                       configurations, fixture)


def verify(executable):
    oracle = DynoOracle(executable)
    original_cases = capture(oracle)
    for case_index, (configuration, observed) in enumerate(
            zip(configurations(), original_cases)):
        mode, cached, previous, neighbors, upward, x, z, seed = configuration
        arena, root, record = fixture(mode, cached, previous, neighbors,
                                      upward, x, z, seed)
        grid = root + bytes(65536 - len(root))
        memory = TrackSurfaceMemory(grid, bytes(arena), BASE)
        world = TrackSurfaceWorld(memory, (0.0, 0.0), (1.0, 1.0),
                                  BLOCKS, PATH, 2, 24)
        result = track_surface_lookup(world, (x, 7.0, z), record)
        expected_result = observed['output'][0]
        expected_record = bytes(observed['output'][1:])
        if result != expected_result or bytes(record) != expected_record:
            mismatches = [i for i, (a, b) in enumerate(zip(record, expected_record)) if a != b]
            raise AssertionError(
                f'0x42e760 Python mismatch case={case_index} mode={mode} '
                f'cached={cached} previous={previous} at bytes '
                f'{[hex(i) for i in mismatches[:16]]}; result {result}/{expected_result}')
    return len(original_cases)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    args = parser.parse_args()
    print(f'Python 0x42e760 record updates match the original for {verify(args.executable)} cases')
