"""Original room disconnect preparation through return or enqueue boundary.

Container resets and enqueue are captured substitutions. Pending waits,
completion pumping, logging, sockets and server operations are excluded.
"""
import argparse
import json
import random
import struct
from client.room_disconnect import prepare_room_disconnect
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    o = DynoOracle(executable)
    cpu, reg = o.cpu, o.reg
    owner = o.inputs
    state = {}

    def boundary(_cpu, address, _size, _user):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        if address in (0x4485f0, 0x456930):
            offset = 0x2e0 if address == 0x4485f0 else 0x1fc
            if cpu.reg_read(reg.UC_X86_REG_ECX) != owner + offset:
                raise AssertionError('original container reset receiver differs')
            state['resets'].append(offset)
            ret = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
            cpu.reg_write(reg.UC_X86_REG_ESP, stack + 4)
            cpu.reg_write(reg.UC_X86_REG_EIP, ret)
        else:
            record, tracked = struct.unpack('<II', cpu.mem_read(stack + 4, 8))
            if cpu.reg_read(reg.UC_X86_REG_ECX) != owner + 12:
                raise AssertionError('original disconnect worker receiver differs')
            kind = struct.unpack('<I', cpu.mem_read(record, 4))[0]
            state['request'] = (kind, bytes(cpu.mem_read(record + 12, 8)), bool(tracked))
            cpu.reg_write(reg.UC_X86_REG_EIP, o.stop)

    hooks = [cpu.hook_add(UC_HOOK_CODE, boundary, begin=a, end=a)
             for a in (0x4485f0, 0x456930, 0x4a5390)]
    rng = random.Random(0x44d750)
    disconnected = connected = 0
    try:
        for status in (0, 1, 0xffff):
            for wait in (False, True):
                for _ in range(16):
                    o._reset()
                    image = bytearray(rng.randbytes(0x3c0))
                    struct.pack_into('<H', image, 0xec, status)
                    struct.pack_into('<I', image, 0x3a8, rng.getrandbits(32) if status == 0 else 0)
                    expected = prepare_room_disconnect(bytes(image), wait_for_completion=wait)
                    cpu.mem_write(owner, bytes(image))
                    cpu.mem_write(0xb36a9c, bytes(4))
                    cpu.reg_write(reg.UC_X86_REG_ECX, owner)
                    stack = cpu.reg_read(reg.UC_X86_REG_ESP)
                    cpu.mem_write(stack, struct.pack('<II', o.stop, wait))
                    state.clear()
                    state.update(resets=[], request=None)
                    o._run(0x44d750, o.stop, count=10000)
                    if bytes(cpu.mem_read(owner, len(image))) != expected.room_image:
                        raise AssertionError('original disconnect reset image differs')
                    if state['resets'] != list(expected.reset_owner_offsets):
                        raise AssertionError('original reset order differs')
                    if status == 0:
                        if state['request'] is not None or cpu.reg_read(reg.UC_X86_REG_EAX) != 0:
                            raise AssertionError('original disconnected return differs')
                        disconnected += 1
                    else:
                        if state['request'] != (1, expected.argument, expected.tracked):
                            raise AssertionError('original disconnect enqueue inputs differ')
                        connected += 1
    finally:
        for hook in hooks:
            cpu.hook_del(hook)
    return {'matched_disconnected_returns': disconnected, 'matched_connected_preparations': connected,
            'substitutions': ['container resets4485f0/456930', 'enqueue4a5390'],
            'excluded': 'pending waits, completion pumping, unspecified task bytes, sockets and live server',
            'live_server_tested': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
