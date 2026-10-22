"""Compare the callback-bounded 0x426d50 initializer to the exact MCO client."""
import argparse
import json
import random
import struct

from client.world_body_initialization import initialize_world_body
from tools.native_oracle import DynoOracle


OBJECT = 0x71001000


def _input(rng, case):
    image = bytearray((rng.randrange(256) for _ in range(0x4F8)))
    start = 0x418
    struct.pack_into('<4f', image, start, rng.uniform(-10, 10),
                     rng.uniform(-10, 10), rng.uniform(-10, 10),
                     rng.uniform(-20, 80))
    struct.pack_into('<9f', image, start + 0x14,
                     1., 0., 0., 0., 1., 0., 0., 0., 1.)
    struct.pack_into('<3f', image, start + 0x38,
                     rng.uniform(.05, 5), rng.uniform(.05, 5), rng.uniform(.05, 5))
    struct.pack_into('<I', image, start + 0x44, rng.randrange(0x10000000))
    struct.pack_into('<HH', image, start + 0x48, case % 5, case % 8)
    struct.pack_into('<I', image, start + 0x50, case * 0x10203)
    struct.pack_into('<9I', image, start + 0x54, *range(case, case + 9))
    struct.pack_into('<f', image, start + 0x78, rng.uniform(-2, 2))
    struct.pack_into('<I', image, start + 0x7C, int(case % 2 == 1))
    struct.pack_into('<f', image, start + 0x80, rng.uniform(-1, 2))
    struct.pack_into('<f', image, start + 0x84, rng.uniform(-1, 2))
    image[start + 0x88:start + 0x92] = b'UNKNOWN\0\0\0'
    return image


def verify(executable, cases=32):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    calls = {0x42E760, 0x51E460, 0x6F28F0}
    def return_stub(cpu, pc, size, _user):
        esp = cpu.reg_read(oracle.reg.UC_X86_REG_ESP)
        ret = struct.unpack('<I', cpu.mem_read(esp, 4))[0]
        cpu.reg_write(oracle.reg.UC_X86_REG_EAX, 0)
        cpu.reg_write(oracle.reg.UC_X86_REG_ESP, esp + 4)
        cpu.reg_write(oracle.reg.UC_X86_REG_EIP, ret)

    hooks = [oracle.cpu.hook_add(UC_HOOK_CODE, return_stub,
                                 begin=address, end=address)
             for address in calls]
    rng = random.Random(0x426D50)
    try:
        for case in range(cases):
            original = _input(rng, case)
            oracle.cpu.mem_write(OBJECT, bytes(original))
            oracle.call(0x426D50, (OBJECT,), instruction_limit=100000)
            expected = bytearray(original)
            initialize_world_body(
                expected, collision_classes={},
                query_surface=lambda _owner, _descriptor, query: query,
                setup_contact=lambda *_args: None,
                geometry_dispatch=lambda *_args: None)
            actual = bytes(oracle.cpu.mem_read(OBJECT, len(expected)))
            if actual != expected:
                mismatch = next(i for i, (a, b) in enumerate(zip(actual, expected)) if a != b)
                raise AssertionError(
                    f'0x426d50 case {case} differs at +{mismatch:#x}: '
                    f'native={actual[mismatch:mismatch+16].hex()} '
                    f'python={expected[mismatch:mismatch+16].hex()}')
    finally:
        for hook in hooks:
            oracle.cpu.hook_del(hook)
    return cases


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=32)
    args = parser.parse_args()
    print(json.dumps({
        'entry': '0x426d50', 'cases': verify(args.executable, args.cases),
        'all_object_bytes_matched': True,
        'query_stack_tail_zero_initialized': True,
        'scope': 'object initialization with surface lookup, contact setup and render dispatch intercepted as child boundaries',
    }))
