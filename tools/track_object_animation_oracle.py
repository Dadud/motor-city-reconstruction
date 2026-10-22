"""Compare FRD object animation sampling against native 0x407940."""
import argparse
import json
from pathlib import Path
import struct

from client.track_mesh import decode_mesh
from client.track_object_animation import evaluate_track_object_animation
from tools.native_oracle import DynoOracle


ANIMATION = 0x74000000
TRANSLATION = 0x74011000
ROTATION = 0x74011010
RESULT = 0x74011040


def verify(executable, track_files, max_objects=64):
    if type(max_objects) is not int or max_objects < 1:
        raise ValueError('object sample limit must be positive')
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    cpu.mem_map(0x74000000, 0x20000)
    samples = []
    for track_file in track_files:
        groups = []
        decode_mesh(Path(track_file).read_bytes(), object_records=groups)
        for group in groups:
            for object_index, obj in enumerate(group.objects):
                if obj.animation and (obj.descriptor[2] & 0xf) == 3:
                    samples.append((track_file, group, object_index, obj.animation))
                    if len(samples) >= max_objects:
                        break
            if len(samples) >= max_objects:
                break
        if len(samples) >= max_objects:
            break
    if not samples:
        raise ValueError('no animated type-3 objects in supplied tracks')
    compared = 0
    max_error = 0.0
    exact_outputs = 0
    for track_file, group, object_index, animation in samples:
        cpu.mem_write(ANIMATION, animation)
        _, period = struct.unpack_from('<HH', animation, 4)
        if period == 0 or period > 400:
            period = 6
        frames, = struct.unpack_from('<H', animation, 4)
        ticks = sorted({0, period // 2, period - 1, period,
                        max(0, (frames - 2) * period + period // 2)})
        for tick in ticks:
            expected = evaluate_track_object_animation(animation, tick)
            result = oracle.call(0x407940,
                                 (ANIMATION, 1, tick, TRANSLATION, ROTATION),
                                 tail=b'\xa3' + struct.pack('<I', RESULT),
                                 instruction_limit=20_000)
            native_result, = struct.unpack('<I', cpu.mem_read(RESULT, 4))
            if native_result != 1:
                raise AssertionError(f'{track_file}: mode 1 returned {native_result}')
            native_translation = struct.unpack('<3f', cpu.mem_read(TRANSLATION, 12))
            native_rotation = struct.unpack('<9f', cpu.mem_read(ROTATION, 36))
            actual = native_translation + native_rotation
            translated = expected.translation + expected.rotation
            errors = tuple(abs(a - b) for a, b in zip(actual, translated))
            error = max(errors)
            max_error = max(max_error, error)
            if error > max(2e-5, max(abs(value) for value in actual) * 2e-6):
                raise AssertionError(
                    f'{track_file} object {group.block_index}:{object_index} '
                    f'tick {tick}: maximum pose error {error}, '
                    f'native={actual!r}, translated={translated!r}')
            exact_outputs += actual == translated
            compared += 1
        final_tick = (frames - 1) * period
        result = oracle.call(0x407940,
                             (ANIMATION, 2, final_tick, TRANSLATION, ROTATION),
                             tail=b'\xa3' + struct.pack('<I', RESULT),
                             instruction_limit=20_000)
        native_result, = struct.unpack('<I', cpu.mem_read(RESULT, 4))
        if native_result != 0 or evaluate_track_object_animation(
                animation, final_tick, mode=2) is not None:
            raise AssertionError(
                f'{track_file} object {group.block_index}:{object_index}: '
                'mode 2 did not stop at the final interval')
    return {'entry': '0x407940', 'objects': len(samples),
            'sample_calls': compared, 'mode_2_final_interval_cases': len(samples),
            'max_abs_float_error': max_error,
            'exact_pose_matches': exact_outputs,
            'source': 'installed FRD type-3 animation payloads'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('tracks', nargs='+')
    parser.add_argument('--max-objects', type=int, default=64)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.tracks, args.max_objects)))
