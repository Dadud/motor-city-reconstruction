"""Compare the translated sky grid topology with 0x4943f0 in mcity.exe."""
import argparse
import json
import struct

from client.sky import sky_material_triangle_indices
from tools.native_oracle import DynoOracle


def verify(executable):
    actual = DynoOracle(executable).sky_material_indices()
    indices = sky_material_triangle_indices()
    expected = bytearray(25*0x138)
    for row in range(25):
        struct.pack_into('<50I', expected, row*0x138, *indices[row*50:(row+1)*50])
    expected = bytes(expected)
    if actual != expected:
        for offset in range(0, len(expected), 4):
            native = struct.unpack_from('<I', actual, offset)[0]
            translated = struct.unpack_from('<I', expected, offset)[0]
            if native != translated:
                raise AssertionError((offset//4, native, translated))
        raise AssertionError('sky index buffer differs')
    return {'indices': len(indices), 'rows': 25, 'matches': True,
            'scope': 'enabled native sky-material topology buffer, including 0x70-byte row padding'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable)))
