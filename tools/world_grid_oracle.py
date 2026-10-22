"""Compare the native 0x552a00/0x5529a0 world-grid relocator."""
import argparse
import json
import struct
from pathlib import Path

from client.track_mesh import decode_mesh
from client.world_grid import fixup_world_grid
from tools.native_oracle import DynoOracle


GRID_TABLE = 0x00A559D8
GRID_BOUNDS = 0x00A55970
SCALE_X = 0x00A659D8
SCALE_Y = 0x00A659DC


def _translated_tail(track_file):
    data = Path(track_file).read_bytes()
    _, mesh_end = decode_mesh(data, materials=True)
    tail = data[mesh_end:]
    translated = fixup_world_grid(tail, 0x71000000)
    return tail, translated, mesh_end


def _compare(oracle, hook, track_file):
    tail, translated, mesh_end = _translated_tail(track_file)
    oracle.cpu.mem_write(oracle.inputs, tail)
    oracle.call(0x552A00, (oracle.inputs,), instruction_limit=10_000_000)
    native_table = bytes(oracle.cpu.mem_read(GRID_TABLE, 0x10000))
    native_payload = bytes(oracle.cpu.mem_read(oracle.inputs + 0x10010,
                                               len(tail) - 0x10010))
    native_bounds = bytes(oracle.cpu.mem_read(GRID_BOUNDS, 0x10))
    native_scales = bytes(oracle.cpu.mem_read(SCALE_X, 8))
    expected_scales = struct.pack('<2f', translated.scale_x, translated.scale_y)
    if native_table != translated.table:
        offset = next(i for i, (a, b) in enumerate(zip(native_table, translated.table)) if a != b)
        raise AssertionError(f'world-grid table mismatch at +{offset:#x}')
    if native_payload != translated.payload:
        offset = next(i for i, (a, b) in enumerate(zip(native_payload, translated.payload)) if a != b)
        raise AssertionError(f'world-grid payload mismatch at +{offset:#x}')
    if native_bounds != tail[:0x10]:
        raise AssertionError('world-grid bounds copy differs')
    if native_scales != expected_scales:
        raise AssertionError(f'world-grid scale mismatch: {native_scales.hex()} != {expected_scales.hex()}')
    cursor = hook['cursors'][-1]
    if cursor != translated.cursor_address:
        raise AssertionError(f'world-grid cursor mismatch: {cursor:#x} != {translated.cursor_address:#x}')
    return {
        'entry': '0x552a00', 'helper': '0x5529a0',
        'track_file': str(track_file), 'mesh_end': mesh_end,
        'tail_bytes': len(tail), 'cursor_bytes': translated.cursor_address - 0x71000000,
        'all_table_and_payload_bytes_matched': True,
    }


def verify_corpus(executable, track_files):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    track_files = tuple(track_files)
    tails = [_translated_tail(path)[0] for path in track_files]
    max_tail = max(map(len, tails), default=0)
    extra = max(0, max_tail - 0x10000)
    extra = (extra + 0xFFF) & ~0xFFF
    if extra:
        oracle.cpu.mem_map(oracle.inputs + 0x10000, extra)
    state = {'cursors': []}

    def capture_cursor(cpu, pc, size, _user):
        state['cursors'].append(cpu.reg_read(oracle.reg.UC_X86_REG_ECX))

    hook = oracle.cpu.hook_add(UC_HOOK_CODE, capture_cursor,
                               begin=0x552B25, end=0x552B25)
    try:
        reports = []
        for index, path in enumerate(track_files):
            if len(state['cursors']) != index:
                raise AssertionError('unexpected world-grid cursor hook count')
            reports.append(_compare(oracle, state, path))
            if len(state['cursors']) != index + 1:
                raise AssertionError('world-grid cursor hook did not run exactly once')
    finally:
        oracle.cpu.hook_del(hook)
    return reports


def corpus_report(executable, track_files):
    reports = verify_corpus(executable, track_files)
    return {
        'entry': '0x552a00', 'helper': '0x5529a0',
        'track_count': len(reports),
        'all_tracks_match': all(r['all_table_and_payload_bytes_matched'] for r in reports),
        'tracks': reports,
    }


def verify(executable, track_file):
    return verify_corpus(executable, [track_file])[0]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('track_file', nargs='+')
    parser.add_argument('--report', help='write the full comparison report as JSON')
    args = parser.parse_args()
    report = corpus_report(args.executable, args.track_file)
    rendered = json.dumps(report if len(args.track_file) != 1 else report['tracks'][0], indent=2)
    if args.report:
        Path(args.report).write_text(rendered + '\n', encoding='utf-8')
    print(rendered)
