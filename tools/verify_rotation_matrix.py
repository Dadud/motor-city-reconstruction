"""Compare the original 0x4b7430 rotation-matrix update to its source port."""
import argparse
from pathlib import Path
import struct

from client.matrix_math import integrate_rotation_matrix
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle=DynoOracle(executable)
    source,destination=oracle.inputs,oracle.inputs+0x100
    cases=(
        ((1,0,0,0,1,0,0,0,1),(0.01,-0.02,0.03)),
        ((0.8,0.1,0, -0.2,0.9,0.1, 0,-0.1,1.1),(0.125,0,-0.25)),
        ((1,2,3,4,5,6,7,8,9),(0,0,0)),
        ((1,0,0,0,1,0,0,0,1),(0.5,-0.25,1.0)),
    )
    for matrix,delta in cases:
        oracle.cpu.mem_write(source,struct.pack('<9f',*matrix))
        oracle.cpu.mem_write(destination,bytes(36))
        float_words=tuple(struct.unpack('<I',struct.pack('<f',value))[0] for value in delta)
        oracle.call(0x004b7430,arguments=(source,*float_words,destination))
        actual=bytes(oracle.cpu.mem_read(destination,36))
        expected=struct.pack('<9f',*integrate_rotation_matrix(matrix,delta))
        if actual!=expected:
            raise AssertionError(f'original rotation matrix mismatch: {actual.hex()} != {expected.hex()}')
    return len(cases)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable',type=Path,help='exact verified original executable')
    args=parser.parse_args()
    print(f'original rotation-matrix update matches for {verify(args.executable)} cases')


if __name__=='__main__':
    main()
