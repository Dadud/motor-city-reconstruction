"""Compare alternate viewport state copies with original 0x474d50."""
import argparse
import random

from client.render_viewport import set_alternate_render_viewport_words
from tools.native_oracle import DynoOracle


def verify(executable,cases=512):
    if type(cases) is not int or not 1<=cases<=20_000:
        raise ValueError('cases must be between 1 and 20000')
    rng=random.Random(0x474d50)
    oracle=DynoOracle(executable)
    for index in range(cases):
        # Raw uint32 inputs cover all binary32 encodings without host float
        # canonicalization, matching the native routine's MOV-only behavior.
        values=tuple(rng.getrandbits(32) for _ in range(6))
        expected=tuple(set_alternate_render_viewport_words(*values).values())
        actual=oracle.alternate_render_viewport_words(values)
        if actual!=expected:
            raise AssertionError(
                f'case {index}: input={values!r}; native={actual!r}; '
                f'expected={expected!r}')
    return cases


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases',type=int,default=512)
    args=parser.parse_args()
    print(f'0x474d50 alternate viewport matches '
          f'{verify(args.executable,args.cases)} cases')


if __name__=='__main__':
    main()
