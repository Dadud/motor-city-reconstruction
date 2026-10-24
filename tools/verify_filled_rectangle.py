"""Compare 0x482700's four clipped vertex records with the MCO executable."""
import argparse
import random

from client.render_clip_code import RenderClipBounds
from client.render_rectangle import plan_filled_rectangle_vertices
from tools.native_oracle import DynoOracle


def verify(executable,cases=512):
    if type(cases) is not int or not 1<=cases<=20_000:
        raise ValueError('cases must be between 1 and 20000')
    rng=random.Random(0x482700)
    oracle=DynoOracle(executable)
    endpoints=(-0x80000000,-0x01000001,-0x01000000,-1,0,1,
               0x00ffffff,0x01000000,0x01000001,0x7fffffff)
    for index in range(cases):
        if index==0:
            # This requires x87 integer addition before binary32 rounding;
            # rounding each operand first would produce zero instead of one.
            x,y,width,height=0x01000001,0,-0x01000000,0
        elif index<=10:
            edge=index-1
            x=endpoints[edge]
            y=endpoints[-edge-1]
            width=endpoints[(edge+3)%len(endpoints)]
            height=endpoints[(edge+7)%len(endpoints)]
        else:
            x,y,width,height=(rng.randint(-0x80000000,0x7fffffff)
                              for _ in range(4))
        bounds=RenderClipBounds(*(rng.randint(-0x80000000,0x7fffffff)
                                  for _ in range(6)))
        attributes=tuple(rng.getrandbits(32) for _ in range(4))
        residue=tuple(tuple(rng.getrandbits(32) for _ in range(3))
                      for _ in range(4))
        modeled=plan_filled_rectangle_vertices(
            x,y,width,height,attributes,bounds,opaque_words=residue)
        expected=tuple((v.x_word,v.y_word,v.z_word,v.w_word,
                        v.attribute_word,*v.clip_tail_words) for v in modeled)
        actual=oracle.render_filled_rectangle(
            (x,y,width,height),attributes,bounds,opaque_words=residue)
        if actual!=expected:
            raise AssertionError(
                f'case {index}: 0x482700 records differ for '
                f'{(x,y,width,height)!r}; expected={expected!r}; actual={actual!r}')
    return cases


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases',type=int,default=512)
    args=parser.parse_args()
    print(f'0x482700 matches {verify(args.executable,args.cases)} direct calls')


if __name__=='__main__':
    main()
