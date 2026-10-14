"""Bounded original channel-reply mailbox and rejection comparisons.

Synthetic state only. The mailbox's serializer call is an explicit substituted
boundary: argument capture and a supplied pointer return, not original encoding.
No sockets, original startup, host callbacks or authenticated sessions execute.
"""
import argparse
import json
import struct

from client.lobby_channel_codec import ChannelJoinRejection, ChannelReplyMailbox
from client.nps_framing import Frame
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    # Data checks confirm the recovered format and the adjacent reply routes.
    if bytes(cpu.mem_read(0x8e0668, 2)) != b'l\0':
        raise AssertionError('rejection reader format differs')
    if struct.unpack('<3I', cpu.mem_read(0x747d40 + 6 * 4, 12)) != (0x74632d,) * 3:
        raise AssertionError('213/214/215 reply-table destinations differ')
    reader_cases = sentinel_cases = mailbox_cases = 0
    statuses = (0, 1, 23, 0x7fffffff, 0x80000000, 0xffffffe9, 0xfffffffe, 0xffffffff)
    for status in statuses:
        oracle._reset()
        source, output = oracle.inputs, oracle.inputs + 0x1000
        payload = struct.pack('>I', status)
        portable = ChannelJoinRejection.from_frame(Frame(0x213, payload))
        cpu.mem_write(source, payload)
        cpu.mem_write(output, bytes(4))
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        cpu.mem_write(stack, struct.pack('<6I', oracle.stop, 0, source, 4, 0x8e0668, output))
        oracle._run(0x7e42e0, oracle.stop, count=10000)
        if struct.unpack('<I', cpu.mem_read(output, 4))[0] != portable.status:
            raise AssertionError('original rejection reader differs')
        if cpu.reg_read(reg.UC_X86_REG_EAX) != 4:
            raise AssertionError('original rejection reader consumed wrong size')
        reader_cases += 1
        oracle._reset()
        cpu.reg_write(reg.UC_X86_REG_EDI, status)
        oracle._run(0x739bb8, 0x739bc2, count=10)
        result = cpu.reg_read(reg.UC_X86_REG_EDI)
        signed = result if result < 0x80000000 else result - 0x100000000
        if signed != portable.native_result:
            raise AssertionError('original rejection result conversion differs')
        sentinel_cases += 1

    capture = []
    returned_pointer = oracle.inputs + 0x4000

    def serialize_boundary(_cpu, _address, _size, _user):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        return_address, opcode, fields = struct.unpack('<3I', cpu.mem_read(stack, 12))
        capture.append((opcode, fields))
        cpu.reg_write(reg.UC_X86_REG_EAX, returned_pointer)
        cpu.reg_write(reg.UC_X86_REG_ESP, stack + 12)  # thiscall callee removes two arguments
        cpu.reg_write(reg.UC_X86_REG_EIP, return_address)

    hook = cpu.hook_add(UC_HOOK_CODE, serialize_boundary, begin=0x7e5e60, end=0x7e5e60)
    try:
        for message_id in (0x213, 0x214, 0x215):
            for waiting in (0, 1, 2, 0xffffffff):
                for completed in (0, 1, 2, 0xffffffff):
                    oracle._reset()
                    capture.clear()
                    server, fields = oracle.inputs, oracle.inputs + 0x2000
                    original_pointer = oracle.inputs + 0x5000
                    cpu.mem_write(server, bytes(0x200))
                    cpu.mem_write(server + 0x18c, struct.pack('<3I', original_pointer, completed, waiting))
                    cpu.mem_write(fields, struct.pack('<II', 0x12345678, 0x87654321))
                    # Exclude diagnostic/logging branch, whose side effects are not tested.
                    cpu.mem_write(0xb38014, bytes(4))
                    stack = cpu.reg_read(reg.UC_X86_REG_ESP)
                    cpu.mem_write(stack + 0x190, struct.pack('<I', fields))
                    cpu.reg_write(reg.UC_X86_REG_EBX, server)
                    cpu.reg_write(reg.UC_X86_REG_EBP, message_id)
                    cpu.reg_write(reg.UC_X86_REG_EDI, 0)
                    accepted = bool(waiting) and not completed
                    stop = 0x7472e7 if accepted else 0x7472e0
                    oracle._run(0x74632d, stop, count=10000)
                    pointer, actual_completed, actual_waiting = struct.unpack('<3I', cpu.mem_read(server + 0x18c, 12))
                    expected_pointer = returned_pointer if accepted else original_pointer
                    if (pointer, actual_completed, actual_waiting) != (expected_pointer, 1 if accepted else completed, waiting):
                        raise AssertionError('original mailbox state differs')
                    if capture != ([(message_id, fields)] if accepted else []):
                        raise AssertionError('original mailbox serializer arguments differ')
                    portable = ChannelReplyMailbox()
                    portable.waiting = bool(waiting)
                    portable.completed = bool(completed)
                    payload = struct.pack('>I', 0x12345678) if message_id == 0x213 else struct.pack('>II', 0x12345678, 0x87654321)
                    if portable.receive(Frame(message_id, payload)) != accepted:
                        raise AssertionError('portable mailbox acceptance differs')
                    if portable.completed != bool(actual_completed) or portable.waiting != bool(actual_waiting):
                        raise AssertionError('portable mailbox flags differ')
                    mailbox_cases += 1
    finally:
        cpu.hook_del(hook)
    return {'matched_rejection_reads': reader_cases, 'matched_rejection_result_conversions': sentinel_cases,
            'matched_mailbox_cases': mailbox_cases, 'verified_reply_table_entries': 3,
            'substituted_boundary': '0x7e5e60 serializer: capture two arguments and return supplied pointer',
            'excluded': 'serializer encoding, diagnostic logging, listener/queue transport, ownership cleanup, timeout/cancel, live joins',
            'live_server_tested': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
