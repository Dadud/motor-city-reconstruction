"""Compare render-head fallback selection against original `0x52d070`."""
import argparse
from pathlib import Path
import struct

from client.model_owner import selected_render_head
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    base = 0x74000000
    cpu.mem_map(base, 0x10000)
    owner = base + 0x1000
    comparisons = 0
    for mask in range(16):
        heads = tuple((base + 0x2000 + index * 0x100) if mask & (1 << index) else 0
                      for index in range(4))
        cpu.mem_write(owner, bytes(0x230))
        cpu.mem_write(owner + 0x21c, struct.pack('<4I', *heads))
        for maximum_index in range(4):
            expected = selected_render_head(heads, maximum_index)
            oracle.call(0x52d070, (maximum_index,), this_pointer=owner,
                        cleanup=b'', instruction_limit=512)
            actual = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
            if actual != expected:
                raise AssertionError((mask, maximum_index, hex(actual), hex(expected)))
            comparisons += 1
    return {'comparisons': comparisons, 'max_error': 0,
            'original_entry': '0x52d070',
            'scope': 'all 16 four-slot occupancy masks at each of four descending search limits'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    print(verify(parser.parse_args().executable))


if __name__ == '__main__':
    main()
