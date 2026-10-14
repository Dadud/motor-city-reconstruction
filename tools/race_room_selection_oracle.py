"""Compare original final race-room edits and join-call argument selection.

Executes two bounded caller ranges and its original unsigned decimal helper.
Starts after the metadata builder and assumes the earlier disconnect succeeded.
Stops before room joining; no callbacks, imports, sockets or live data execute.
"""
import argparse
import json
import random
import struct

from client.race_room_selection import prepare_race_room_selection
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu,reg = oracle.cpu,oracle.reg
    app,component,descriptor = oracle.inputs,oracle.inputs + 0x1000,oracle.inputs + 0x3000
    cpu.mem_write(0x9e1060,struct.pack('<I',app))
    cpu.mem_write(app + 0x424,struct.pack('<I',component))
    rng = random.Random(0x5e4870)
    cases = rewrites = 0
    for mode in (0,0x12,0x13,0x14,0x19,0x1a,0xffffffff):
        for channel in (0,1,0x7fffffff,0x80000000,0xffffffff):
            for name in (b'',b'r',b'n' * 31):
                for password in (b'',b'p' * 16):
                    oracle._reset()
                    metadata = rng.randbytes(0xcc)
                    value_78,value_90,value_a8,ready = (rng.getrandbits(32) for _ in range(4))
                    expected = prepare_race_room_selection(metadata,game_mode=mode,room_name=name,
                        channel_id=channel,ready_value=ready,password=password,value_0x78=value_78,
                        value_0x90=value_90,value_0xa8=value_a8)
                    cpu.mem_write(oracle.frame - 0x124,metadata)
                    for address,value in ((0x9aa92c,value_78),(0x9aa978,value_90),
                            (0x9aa97c,value_a8),(0x9aa9b0,mode),(0x9aa9d0,channel),(0x9aaa48,ready)):
                        cpu.mem_write(address,struct.pack('<I',value))
                    cpu.mem_write(0x9aa9d4,name + bytes(64 - len(name)))
                    cpu.mem_write(descriptor + 0x41,password + b'\0')
                    cpu.mem_write(oracle.frame - 0x48,struct.pack('<I',descriptor))
                    cpu.reg_write(reg.UC_X86_REG_EBX,0)
                    # Original caller's mask and three overwrite fields.
                    oracle._run(0x5e4948,0x5e497b,count=1000)
                    if bytes(cpu.mem_read(oracle.frame - 0x124,0xcc)) != expected.metadata:
                        raise AssertionError('original race metadata edits differ')
                    # Successful-disconnect continuation; actual _ultoa executes.
                    oracle._run(0x5e4a13,0x5e4a72,count=10000)
                    stack = cpu.reg_read(reg.UC_X86_REG_ESP)
                    name_ptr,password_ptr,data_ptr,size,ready_arg,channel_arg = struct.unpack('<6I',cpu.mem_read(stack,24))
                    if (name_ptr,password_ptr,data_ptr,size,ready_arg,channel_arg) != (
                            0x9aa9d4,descriptor + 0x41,oracle.frame - 0x124,0xcc,ready,channel):
                        raise AssertionError('original room join caller arguments differ')
                    if cpu.reg_read(reg.UC_X86_REG_ECX) != component + 0xdc0:
                        raise AssertionError('original room join caller receiver differs')
                    actual_name = bytes(cpu.mem_read(name_ptr,32)).split(b'\0',1)[0]
                    if actual_name != expected.name:
                        raise AssertionError('original room name override differs')
                    if bytes(cpu.mem_read(data_ptr,size)) != expected.metadata:
                        raise AssertionError('original metadata changed after name override')
                    cases += 1
                    rewrites += int(mode in (0x13,0x19) and channel != 0)
    return {'matched_race_room_selection_cases':cases,'matched_unsigned_name_overrides':rewrites,
            'original_decimal_helper_executed':True,'live_server_tested':False,
            'coverage':'5e4948..5e497b and5e4a13..5e4a72; stops before4509c0',
            'excluded':'metadata builder62f740, preceding room validation/disconnect, descriptor ownership, join, postjoin synchronization'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable),indent=2))
