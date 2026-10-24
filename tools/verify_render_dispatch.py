"""Compare render-mode flag and callback dispatch at 0x6f28f0."""
import argparse
import random
from pathlib import Path

from client.render_mode_dispatch import RenderDispatchState, dispatch_render_mode
from tools.native_oracle import DynoOracle


def make_state(rng, *, cached_mode=None, forced=None):
    primary = [rng.getrandbits(1) for _ in range(32)]
    secondary = [rng.getrandbits(1) for _ in range(8)]
    for index, value in (forced or {}).items():
        (primary if index[0] == 'p' else secondary)[index[1]] = value
    return RenderDispatchState(
        cached_mode=rng.getrandbits(32) if cached_mode is None else cached_mode,
        capability_bit_4=rng.getrandbits(32), capability_bit_2=rng.getrandbits(32),
        capability_bit_0x10000=rng.getrandbits(32),
        capability_bit_0x20000_a=rng.getrandbits(32),
        capability_bit_0x20000_b=rng.getrandbits(32),
        capability_both_0x30000=rng.getrandbits(32),
        capability_bit0=rng.getrandbits(32),
        callback_context_b=rng.getrandbits(32),
        vertex_stride=rng.getrandbits(32), vertex_format=rng.getrandbits(32),
        primary_callbacks=tuple(primary), secondary_callbacks=tuple(secondary),
        render_flags=rng.getrandbits(32), primary_callback=rng.getrandbits(1),
        secondary_callback=rng.getrandbits(1),
        draw_context_a=rng.getrandbits(32), draw_context_b=rng.getrandbits(32),
        draw_param3=rng.getrandbits(32), draw_param4=rng.getrandbits(32))


def verify(executable, cases=512):
    oracle = DynoOracle(executable)
    rng = random.Random(0x6f28f0)
    vectors = []
    # Force both callback table routes and the same-mode cache shortcut.
    for mode in (0, 1, 0x20000, 0x30000, 0x30001, 0x30002, 0x10004):
        active = mode
        state = make_state(rng, cached_mode=0xffffffff,
                           forced={('p', active & 31):1,
                                   ('s', ((active >> 15)&7)|(active&1)):1})
        vectors.append((state, mode, 7, 0x123400, 0x567800))
    state = make_state(rng, cached_mode=0x12345678)
    vectors.append((state, state.cached_mode, 7, 0x123400, 0x567800))
    # Invalid argument gates must return zero without calling either callback.
    state = make_state(rng, cached_mode=0xffffffff,
                       forced={('p', 0):1, ('s', 0):1})
    vectors.extend((state, 0, count, vertices, indices) for count,vertices,indices in
                   ((0,0x123400,0x567800),(7,0,0x567800),(7,0x123400,0)))
    vectors.extend((make_state(rng), rng.getrandbits(32), rng.randrange(0,9),
                    rng.choice((0,0x123400,0x100000)),
                    rng.choice((0,0x567800,0x200000)))
                   for _ in range(max(0,cases-len(vectors))))
    for index, (state,mode,count,vertices,indices) in enumerate(vectors):
        expected_result, expected_state, events = dispatch_render_mode(
            state, mode, count, vertices, indices)
        result, actual_state, captured = oracle.render_dispatch(
            state, mode, count, vertices, indices)
        expected_globals = {
            'cached_mode':expected_state.cached_mode,
            'vertex_stride':expected_state.vertex_stride,
            'vertex_format':expected_state.vertex_format,
            'render_flags':expected_state.render_flags,
            'primary_callback':int(bool(expected_state.primary_callback)),
            'secondary_callback':int(bool(expected_state.secondary_callback)),
            'draw_context_a':expected_state.draw_context_a,
            'draw_context_b':expected_state.draw_context_b,
            'draw_param3':expected_state.draw_param3,
            'draw_param4':expected_state.draw_param4}
        if result != expected_result or actual_state != expected_globals:
            raise AssertionError((index, 'state', result, expected_result, actual_state, expected_globals))
        primary = next((e for e in events if e[0]=='primary'), None)
        secondary = next((e for e in events if e[0]=='secondary'), None)
        expected_capture = (int(primary is not None),
            primary[1] if primary else 0, primary[2] if primary else 0,
            primary[3] if primary else 0, int(secondary is not None),
            secondary[1] if secondary else 0, secondary[2] if secondary else 0, 0)
        if captured != expected_capture:
            raise AssertionError((index, 'callback args', captured, expected_capture))
    return len(vectors)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    if not 10 <= args.cases <= 4096:
        parser.error('--cases must be within [10, 4096]')
    print(f'0x6f28f0 matches {verify(args.executable, args.cases)} direct calls')

