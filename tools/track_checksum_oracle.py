"""Compare the loader CRC routine 0x658280 with the authored checksum."""
import argparse
import json
import random
from pathlib import Path

from client.track_checksum import track_checksum
from tools.native_oracle import DynoOracle


MAX_INPUT = 0x10000
INPUT_WINDOW = 0x01000000


def _native_checksum(oracle, data):
    oracle._reset()
    stack = oracle.frame - 0x1000
    oracle.cpu.mem_write(stack, oracle.stop.to_bytes(4, 'little'))
    oracle.cpu.reg_write(oracle.reg.UC_X86_REG_ESP, stack)
    oracle.cpu.reg_write(oracle.reg.UC_X86_REG_EBP, oracle.frame)
    # cdecl pushes the second argument first: (length, input_pointer).
    code = b'\x68' + oracle.inputs.to_bytes(4, 'little')
    code += b'\x68' + len(data).to_bytes(4, 'little')
    call_at = oracle.stub + len(code)
    call_end = call_at + 5
    code += b'\xe8' + (0x658280-call_end).to_bytes(4, 'little', signed=True)
    code += b'\x83\xc4\x08\xc3'
    oracle.cpu.mem_write(oracle.stub, code)
    if hasattr(oracle.cpu, 'ctl_flush_tb'):
        oracle.cpu.ctl_flush_tb()
    oracle._run(oracle.stub, oracle.stop, timeout=0,
                count=len(data)*12+5_000)
    return oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)


def compare(executable, track_files=()):
    oracle = DynoOracle(executable)
    rng = random.Random(0x658280)
    cases = [b'', b'\0', b'a', b'123456789', bytes(range(256)),
             bytes(range(256))*256, rng.randbytes(MAX_INPUT)]
    tracks = []
    for path in track_files:
        data = Path(path).read_bytes()
        tracks.append((f'{Path(path).parent.name}/{Path(path).name}', data))
    maximum = max((len(data) for data in cases + [data for _, data in tracks]),
                  default=0)
    if maximum >= INPUT_WINDOW:
        raise ValueError('checksum input exceeds the bounded 16 MiB oracle window')
    if maximum > MAX_INPUT:
        extra = (maximum-MAX_INPUT+0xfff) & ~0xfff
        oracle.cpu.mem_map(oracle.inputs+MAX_INPUT, extra)

    all_cases = cases + [data for _, data in tracks]
    for index, data in enumerate(all_cases):
        oracle.cpu.mem_write(oracle.inputs, data if data else b'\0')
        native = _native_checksum(oracle, data)
        translated = track_checksum(data)
        if native != translated:
            raise AssertionError(
                f'case {index}, {len(data)} bytes: native {native:#010x} '
                f'!= translated {translated:#010x}')
    return {
        'entry': '0x658280',
        'cases_matched': len(all_cases),
        'bytes_compared': sum(map(len, all_cases)),
        'complete_track_files': [name for name, _ in tracks],
        'track_file_bytes': sum(len(data) for _, data in tracks),
        'raw_accumulator_matched': True,
        'scope': 'original checksum function emulated on bounded byte buffers; '
                 'native file APIs and whole-loader behavior are excluded',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--track-root', type=Path)
    args = parser.parse_args()
    files = ()
    if args.track_root:
        files = tuple(sorted(args.track_root.glob('*/Tr.frd')))
    print(json.dumps(compare(args.executable, files)))
