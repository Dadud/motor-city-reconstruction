"""Compare track-backed projection passthrough with original MCO execution."""
import argparse
import random
import struct

from client.render_projection import track_point_without_cached_geometry
from tools.native_oracle import DynoOracle


def verify(executable,cases=512):
    if type(cases) is not int or not 1<=cases<=10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle=DynoOracle(executable)
    rng=random.Random(0x42dc50)
    for case in range(cases):
        rows=[]
        row_count=1+case%8
        for _ in range(row_count):
            row=bytearray(rng.getrandbits(8) for _ in range(0x54))
            for offset in (0,4,8):
                struct.pack_into('<f',row,offset,rng.uniform(-1e4,1e4))
            rows.append(bytes(row))
        index=rng.randrange(row_count)
        expected=track_point_without_cached_geometry(rows,index,0)
        actual=oracle.track_point_without_cached_geometry(rows,index)
        expected_words=struct.pack('<3f',*expected)
        actual_words=struct.pack('<3f',*actual)
        if actual_words!=expected_words:
            raise AssertionError(f'projection passthrough case {case}, row {index}: expected {expected_words.hex()}, got {actual_words.hex()}')
    return {'native-matching-track-point-passthrough-cases':cases}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases',type=int,default=512)
    args=parser.parse_args()
    print(verify(args.executable,args.cases))


if __name__=='__main__':
    main()
