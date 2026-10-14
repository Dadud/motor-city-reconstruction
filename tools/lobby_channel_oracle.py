"""Compare channel payload bytes with bounded original x86 execution.

Synthetic local records only: no sockets, credentials, or executable startup.
"""
import argparse
import json
import random
import struct

from client.lobby_channel_codec import ChannelJoinRecord, ChannelJoinSuccess, NATIVE_RECORD_SIZE
from client.nps_framing import Frame
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    randomizer = random.Random(106)
    matched = rejected = 0
    for name_size, text_size in ((0, 0), (1, 1), (31, 17), (15, 9)):
        for mode in range(9):
            record = bytearray(randomizer.randbytes(NATIVE_RECORD_SIZE))
            if mode == 0:
                record[:] = bytes(NATIVE_RECORD_SIZE)
            elif mode == 1:
                record[:] = bytes([255]) * NATIVE_RECORD_SIZE
            record[4:0x24] = b'n' * name_size + bytes(32 - name_size)
            record[0x74:0x86] = b't' * text_size + bytes(18 - text_size)
            case = ChannelJoinRecord(bytes(record))
            oracle._reset()
            source, output, context = oracle.inputs, oracle.inputs + 0x1000, oracle.inputs + 0x2000
            cpu.mem_write(source, case.native)
            cpu.mem_write(output, bytes(0x400))
            cpu.mem_write(context, bytes(16))
            cpu.reg_write(reg.UC_X86_REG_ECX, context)
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.mem_write(stack, struct.pack('<4I', oracle.stop, output, 0x170, source))
            oracle._run(0x7e4c30, oracle.stop, count=100000)
            size = cpu.reg_read(reg.UC_X86_REG_EAX)
            try:
                expected = case.payload()
            except ValueError:
                if size != 0xffffffff:
                    raise ValueError('original serializer did not reject oversized payload')
                rejected += 1
                continue
            if size != len(expected) or bytes(cpu.mem_read(output, size)) != expected:
                actual = bytes(cpu.mem_read(output, min(size, 0x400)))
                mismatch = next((i for i, pair in enumerate(zip(actual, expected)) if pair[0] != pair[1]), None)
                raise ValueError(f'channel payload differs: native={size}, portable={len(expected)}, first={mismatch}')
            matched += 1
    replies = 0
    for message_id in (0x214, 0x215):
        for channel_id, value in ((0, 0), (1, 255), (0xffffffff, 0x87654321)):
            oracle._reset()
            source, output = oracle.inputs, oracle.inputs + 0x1000
            payload = struct.pack('>II', channel_id, value)
            expected = ChannelJoinSuccess.from_frame(Frame(message_id, payload))
            cpu.mem_write(source, payload)
            cpu.mem_write(output, bytes(8))
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.mem_write(stack, struct.pack('<7I', oracle.stop, 0, source, 8,
                                            0x8e0674, output, output + 4))
            oracle._run(0x7e42e0, oracle.stop, count=100000)
            actual = struct.unpack('<II', cpu.mem_read(output, 8))
            if actual != (expected.channel_id, expected.value_2) or cpu.reg_read(reg.UC_X86_REG_EAX) != 8:
                raise ValueError('channel reply fields differ from original reader')
            replies += 1
    return {'matched_cases': matched, 'matched_capacity_rejections': rejected,
            'matched_reply_field_cases': replies,
            'coverage': '0x7e4c30 payload serializer and ll reply field reader; synthetic records; no live room join'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
