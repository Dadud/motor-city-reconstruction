"""Compare the environment activity transition with the original binary."""
import argparse

from client.render_environment import set_environment_activity
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle=DynoOracle(executable)
    cases=((0,0),(0x71001000,0),(0,0x71002000),
           (0x71003000,0x71004000))
    for primary,secondary in cases:
        expected=tuple((int(bool(pointer)),0)[index]
                       if pointer else None
                       for index,pointer in enumerate((primary,secondary)))
        writes=set_environment_activity(primary,secondary)
        actual=oracle.render_environment_activity(primary,secondary)
        modeled=tuple(None if write is None else write[1] for write in writes)
        if actual!=expected or modeled!=expected:
            raise AssertionError(f'{(primary,secondary)!r}: expected {expected!r}, got native={actual!r}, model={modeled!r}')
    return {'native-matching-environment-activity-configurations':len(cases)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    args=parser.parse_args()
    print(verify(args.executable))


if __name__=='__main__':
    main()
