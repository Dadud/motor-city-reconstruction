"""Write an authored tetrahedron VIV/FCE fixture for native renderer CI.

This is synthetic geometry, not a car or an original game asset. Output is
intended for an ignored build directory. No source installation is needed.
"""
import argparse
from pathlib import Path
import struct


def write_fixture(root: Path) -> Path:
    header = 0x2038
    positions = ((-1., -.6, -.6), (1., -.6, -.6), (0., 1., -.6), (0., 0., 1.))
    faces = ((0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3))
    fce = bytearray(header + len(positions)*24 + len(faces)*56)
    def word(offset, value):
        struct.pack_into('<I', fce, offset, value)
    word(0, 0x101014)
    word(8, len(faces))
    word(12, len(positions))
    word(0x18, len(positions)*12)
    word(0x1c, len(positions)*24)
    word(0x11c, 1)
    word(0x520, len(positions))
    word(0x720, len(faces))
    fce[0xe28:0xe28+10] = b'SYNTHETIC\0'
    for i, position in enumerate(positions):
        struct.pack_into('<3f', fce, header+i*12, *position)
        struct.pack_into('<3f', fce, header+len(positions)*12+i*12, 0., 1., 0.)
    for i, indices in enumerate(faces):
        struct.pack_into('<4I', fce, header+len(positions)*24+i*56, 0, *indices)
    name = b'part.fce\0'
    offset = 16+8+len(name)
    archive = struct.pack('>4sIII', b'BIGF', offset+len(fce), 1, offset)
    archive += struct.pack('>II', offset, len(fce))+name+fce
    target = root/'Data'/'Models'/'synthetic.viv'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(archive)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output_root', type=Path)
    args = parser.parse_args()
    print(write_fixture(args.output_root))
