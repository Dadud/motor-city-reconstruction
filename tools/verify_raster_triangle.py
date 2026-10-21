"""Compare 0x483c70's triangle vertex ordering with the original executable."""
import argparse
import itertools
import random
import struct
import subprocess
from pathlib import Path

from client.raster_triangle import order_triangle_vertices_by_y
from tools.native_oracle import DynoOracle


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def words(vertices):
    return tuple(bits(value) for point in vertices for value in point)


def verify(executable, native_runner=None):
    oracle = DynoOracle(executable)
    outputs = tuple(oracle.inputs+0x1000+index*4 for index in range(6))
    rng = random.Random(0x483C70)
    vertices = []
    for ys in ((10,20,30),(10,10,30),(10,30,30),(10,10,10),
               (30,10,10),(20,10,20),(20,20,10)):
        vertices.extend(tuple((float(index+1),float(y)) for index,y in enumerate(order))
                        for order in itertools.permutations(ys))
    vertices.extend(tuple((rng.uniform(-320,320),rng.randint(0,240)) for _ in range(3))
                     for _ in range(256))

    for case, points in enumerate(vertices):
        original_words = words(points)
        oracle.call(0x00483c70, (*original_words, *outputs))
        original = tuple(struct.unpack('<I', oracle.cpu.mem_read(address,4))[0]
                         for address in outputs)
        expected = words(order_triangle_vertices_by_y(points))
        if original != expected:
            raise AssertionError(f'Python mismatch at case {case}: '
                                 f'{original!r} != {expected!r}; input={points!r}')
        if native_runner is not None:
            line=' '.join(f'{word:08x}' for word in original_words)+'\n'
            result=subprocess.run([str(native_runner)],input=line,text=True,
                                  capture_output=True,check=True)
            native=tuple(int(word,16) for word in result.stdout.split())
            if native != expected:
                raise AssertionError(f'native mismatch at case {case}: '
                                     f'{native!r} != {expected!r}')
    return len(vertices)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable',type=Path)
    parser.add_argument('--native-runner',type=Path)
    args=parser.parse_args()
    count=verify(args.executable,args.native_runner)
    print(f'0x483c70 matches for {count} triangle vertex sets')


if __name__=='__main__': main()
