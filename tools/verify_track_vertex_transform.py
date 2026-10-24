"""Compare track mesh per-vertex transforms with original x87 dot products."""
import argparse
import random
import struct
from pathlib import Path

from client.track_vertex_transform import transform_track_vertex
from tools.native_oracle import DynoOracle


def verify(executable, cases=512):
    oracle = DynoOracle(executable)
    rng = random.Random(0x495c00)
    vectors = [((1.,2.,3.), (1.,0.,0.,0.,1.,0.,0.,0.,1.)),
               ((2.,3.,5.), (1.,2.,3.,4.,5.,6.,7.,8.,9.)),
               ((1e20,1.,-1e20), (1.,1.,1.,1.,1.,1.,1.,1.,1.))]
    vectors.extend((tuple(rng.uniform(-1e5,1e5) for _ in range(3)),
                    tuple(rng.uniform(-10,10) for _ in range(9)))
                   for _ in range(max(0,cases-len(vectors))))
    for index,(vertex,matrix) in enumerate(vectors):
        expected=tuple(oracle.dot3(vertex,(matrix[c],matrix[c+3],matrix[c+6]))
                       for c in range(3))
        actual=transform_track_vertex(vertex,matrix)
        if struct.pack('<3f',*actual)!=struct.pack('<3f',*expected):
            raise AssertionError((index,vertex,matrix,actual,expected))
    return len(vectors)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable',type=Path)
    parser.add_argument('--cases',type=int,default=512)
    args=parser.parse_args()
    if not 3<=args.cases<=4096:
        parser.error('--cases must be within [3,4096]')
    print(f'track vertex transform matches {verify(args.executable,args.cases)} native cases')
