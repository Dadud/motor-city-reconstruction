"""Compare 0x483e80 scanline intersections with the original executable."""
import argparse
import random
import struct
import subprocess
from pathlib import Path

from client.raster_intersection import raster_scanline_intersections
from tools.native_oracle import DynoOracle


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def verify(executable, native_runner=None):
    oracle = DynoOracle(executable)
    outputs = (oracle.inputs+0x1000, oracle.inputs+0x1004)
    rng = random.Random(0x483E80)
    cases = [
        (((1,0),(5,10)), ((10,0),(14,10)), y)
        for y in (0, 2.5, 5, 7.5, 10)
    ]
    cases.extend(
        (((rng.uniform(-100,100), y1), (rng.uniform(-100,100), y2)),
         ((rng.uniform(-100,100), z1), (rng.uniform(-100,100), z2)),
         rng.uniform(max(min(y1,y2),min(z1,z2)), min(max(y1,y2),max(z1,z2))))
        for _ in range(512)
        for y1,y2,z1,z2 in [(rng.uniform(-200,100),rng.uniform(101,300),
                             rng.uniform(-200,100),rng.uniform(101,300))]
    )
    for case, (edge_a, edge_b, scan_y) in enumerate(cases):
        values = tuple(value for edge in (edge_a,edge_b) for point in edge
                       for value in point)+(scan_y,)
        input_words = tuple(bits(value) for value in values)
        oracle.call(0x00483e80, (*input_words, *outputs))
        original = tuple(struct.unpack('<I', oracle.cpu.mem_read(address,4))[0]
                         for address in outputs)
        expected = tuple(bits(value) for value in
                         raster_scanline_intersections(edge_a,edge_b,scan_y))
        if original != expected:
            raise AssertionError(f'Python mismatch at case {case}: '
                                 f'{original!r} != {expected!r}; '
                                 f'{edge_a!r}, {edge_b!r}, {scan_y!r}')
        if native_runner is not None:
            line=' '.join(f'{word:08x}' for word in input_words)+'\n'
            result=subprocess.run([str(native_runner)],input=line,text=True,
                                  capture_output=True,check=True)
            native=tuple(int(word,16) for word in result.stdout.split())
            if native != expected:
                raise AssertionError(f'native mismatch at case {case}: '
                                     f'{native!r} != {expected!r}')
    return len(cases)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable',type=Path)
    parser.add_argument('--native-runner',type=Path)
    args=parser.parse_args()
    count=verify(args.executable,args.native_runner)
    print(f'0x483e80 matches for {count} edge/scanline inputs')


if __name__=='__main__': main()
