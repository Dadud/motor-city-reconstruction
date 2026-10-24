"""Compare renderer callback 0x6f1d60 with the installed client."""
import argparse
import random
import struct
from pathlib import Path

from client.track_renderer_callbacks import transform_render_positions
from tools.native_oracle import DynoOracle


def verify(executable,cases=512):
    rng=random.Random(0x6f1d60)
    vertices=[(0,0,10),(1,-1,2),(-4,3,0),(100,-200,-50)]
    vertices.extend((rng.uniform(-1000,1000),rng.uniform(-1000,1000),
                     rng.uniform(0.01,500)) for _ in range(max(0,cases-len(vertices))))
    oracle=DynoOracle(executable)
    for source_stride,output_stride in ((12,16),(16,20),(24,32)):
        actual,padding,source_after,output_after=oracle.render_positions(
            vertices,source_stride=source_stride,output_stride=output_stride)
        expected=transform_render_positions(vertices)
        for index,(got,want) in enumerate(zip(actual,expected)):
            if struct.pack('<4f',*got)!=struct.pack('<4f',*want):
                raise AssertionError((source_stride,output_stride,index,got,want))
        if source_after!=oracle.inputs+0x1000+len(vertices)*source_stride:
            raise AssertionError(('source stride',source_stride,source_after))
        if output_after!=oracle.inputs+0x9000+len(vertices)*output_stride:
            raise AssertionError(('output stride',output_stride,output_after))
        if any(any(byte!=0xcd for byte in row) for row in padding):
            raise AssertionError(('output padding overwritten',output_stride))
    return len(vertices)*3


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable',type=Path)
    parser.add_argument('--cases',type=int,default=512)
    args=parser.parse_args()
    if not 4<=args.cases<=2048:parser.error('--cases must be within [4,2048]')
    print(f'0x6f1d60 matches {verify(args.executable,args.cases)} vertices across three stride pairs')
