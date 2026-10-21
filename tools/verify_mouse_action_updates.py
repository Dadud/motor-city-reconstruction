"""Differentially compare action-edge and transition-ring updates with mcity."""
import argparse
import random
import struct
from pathlib import Path

from client.keyboard_action_state import is_keyboard_action_active
from client.mouse_action_updates import MouseActionUpdateState, apply_transition_frame
from tools.native_oracle import DynoOracle


PRIORITY_ACTIONS = 0x009E1D08
FRAME_ACTIONS = 0x009E1D68
EDGE_LATCHES = 0x009E1E70
FRAME_OUTPUT = 0x009E1E89
RING_COUNTER = 0x009E1E80
RING_WORDS = 0x009E1700
ACTION_TABLE = 0x0098E450
KEY_STATES = 0x008C8648
DIRECTION_FLAGS = 0x0098E390
ACTION_DISPATCH = 0x0088E648
CALLBACK_STUB = 0x7100A000
NOTIFY = 0x7100B000
ENVIRONMENT_GATE = 0x00567DC0
NOTIFY_FUNCTION = 0x00576AA0
ENTRY = 0x004ADDA2
RETURN = 0x004AE07B


def _return(cpu, reg, value):
    sp = cpu.reg_read(reg.UC_X86_REG_ESP)
    target = struct.unpack('<I', cpu.mem_read(sp, 4))[0]
    cpu.reg_write(reg.UC_X86_REG_EAX, value & 0xffffffff)
    cpu.reg_write(reg.UC_X86_REG_ESP, sp + 4)
    cpu.reg_write(reg.UC_X86_REG_EIP, target)


def compare(executable, cases=256):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x4ad6f0)
    callbacks = {}
    observed_callbacks = []
    observed_notifications = []
    env_result = {'value': 0}

    def hook(machine, address, _size, _user):
        sp = machine.reg_read(reg.UC_X86_REG_ESP)
        if address == CALLBACK_STUB:
            action = struct.unpack('<I', machine.mem_read(sp + 4, 4))[0]
            observed_callbacks.append(action)
            _return(machine, reg, callbacks.get(action, 0))
        elif address == ENVIRONMENT_GATE:
            _return(machine, reg, env_result['value'])
        elif address == NOTIFY_FUNCTION:
            payload = struct.unpack('<I', machine.mem_read(sp + 4, 4))[0]
            observed_notifications.append(bytes(machine.mem_read(payload, 5)))
            _return(machine, reg, 0)

    hook_ids = [cpu.hook_add(UC_HOOK_CODE, hook, begin=address, end=address)
                for address in (CALLBACK_STUB, ENVIRONMENT_GATE, NOTIFY_FUNCTION)]
    frame = oracle.frame
    cpu.mem_write(ACTION_DISPATCH - 0x200,
                  struct.pack('<I', CALLBACK_STUB) * 256)
    for signed in range(-128, 128):
        cpu.mem_write(ACTION_DISPATCH + signed * 4,
                      struct.pack('<I', CALLBACK_STUB))

    try:
        for case in range(cases):
            oracle._reset()
            edge_image = rng.randbytes(13)
            edge_words = [rng.choice((0, 0, 0x00000101, 0x01000204,
                                      0x07000307, 0x04000404))
                          for _ in range(12)]
            frame_words = [rng.choice((0, 0, 0x401, 0x802, 0xc04, 0x1234))
                           for _ in range(32)]
            priority_bytes = struct.pack('<12I', *edge_words)
            frame_bytes = struct.pack('<32I', *frame_words)
            action_table = bytearray(rng.randbytes(0x7fc))
            key_states = rng.randbytes(0x80)
            direction_mask = rng.getrandbits(32)
            other_results = {a: rng.getrandbits(32)
                             for a in set(edge_words + frame_words) if a}
            callbacks.clear()
            callbacks.update(other_results)
            for action in set(edge_words + frame_words):
                if action and action & 0xff not in (1, 4):
                    signed = (action & 0xff) if action & 0xff < 0x80 else (action & 0xff) - 0x100
                    cpu.mem_write(ACTION_DISPATCH + signed * 4,
                                  struct.pack('<I', CALLBACK_STUB))

            controller_ok = True
            env_result['value'] = 0
            notification_suppressed = 0
            ring_counter = rng.choice((rng.getrandbits(32), 0xfffffffe, 0xffffffff))
            ring_initial = [rng.getrandbits(32) for _ in range(32)]
            notification_payload = rng.randbytes(5)
            mapping_enabled = tuple(bool(rng.randrange(2)) for _ in range(3))
            mapping_values = tuple(rng.choice((2, 5, 6, 9, 10, 11, 12)) for _ in range(3))
            button_flags = rng.randrange(256)
            notification_payload = notification_payload[:3] + bytes((button_flags,)) + notification_payload[4:]

            cpu.mem_write(PRIORITY_ACTIONS, priority_bytes)
            cpu.mem_write(FRAME_ACTIONS, frame_bytes)
            cpu.mem_write(EDGE_LATCHES, edge_image)
            cpu.mem_write(FRAME_OUTPUT, notification_payload)
            cpu.mem_write(FRAME_OUTPUT + 3, bytes((button_flags,)))
            cpu.mem_write(RING_COUNTER, struct.pack('<I', ring_counter))
            cpu.mem_write(RING_WORDS, struct.pack('<32I', *ring_initial))
            cpu.mem_write(ACTION_TABLE, bytes(action_table))
            cpu.mem_write(KEY_STATES, key_states)
            cpu.mem_write(DIRECTION_FLAGS, struct.pack('<I', direction_mask))
            cpu.mem_write(0x009E1644, struct.pack('<I', int(controller_ok)))
            cpu.mem_write(0x009E1640, struct.pack('<I', int(controller_ok)))
            cpu.mem_write(0x00AA459C, bytes((notification_suppressed,)))
            cpu.mem_write(0x009E1654, struct.pack('<I', int(mapping_enabled[0])))
            cpu.mem_write(0x009E165C, struct.pack('<I', int(mapping_enabled[1])))
            cpu.mem_write(0x009E1658, struct.pack('<I', int(mapping_enabled[2])))
            cpu.mem_write(0x009E1648, struct.pack('<I', mapping_values[0]))
            cpu.mem_write(0x009E1650, struct.pack('<I', mapping_values[1]))
            cpu.mem_write(0x009E164C, struct.pack('<I', mapping_values[2]))
            cpu.mem_write(0x009E1E71, bytes((rng.randrange(2), rng.randrange(2))))
            cpu.mem_write(frame - 8, struct.pack('<I', PRIORITY_ACTIONS))
            cpu.mem_write(frame - 1, bytes((button_flags,)))
            cpu.mem_write(frame, struct.pack('<II', 0x72001000, oracle.stop))
            cpu.reg_write(reg.UC_X86_REG_EBP, frame)
            # Recreate ESP after the omitted prologue (16-byte locals plus
            # saved EBX/ESI/EDI); call arguments must not overwrite locals.
            cpu.reg_write(reg.UC_X86_REG_ESP, frame - 0x1c)
            cpu.reg_write(reg.UC_X86_REG_EBX, FRAME_ACTIONS)
            cpu.reg_write(reg.UC_X86_REG_ESI, 0xffffffe5)
            cpu.reg_write(reg.UC_X86_REG_EDI, 0)

            edge_state = bytearray(cpu.mem_read(EDGE_LATCHES, 13))
            notification_calls = []
            state = MouseActionUpdateState(
                edge_latches=edge_state, ring_words=list(ring_initial),
                ring_counter=ring_counter,
                notification_suppressed=notification_suppressed,
                notification_payload=notification_payload,
                button_transition_flags=button_flags)
            action_results = dict(other_results)
            source_callbacks = []

            def active(action):
                if action & 0xff in (1, 4):
                    return is_keyboard_action_active(action, key_states=key_states,
                        direction_flags=direction_mask, action_table=action_table)
                source_callbacks.append(action)
                return action_results[action]

            source = apply_transition_frame(
                state, priority_bytes, frame_bytes, action_active=active,
                direction_enabled=True,
                direction_codes=mapping_enabled, direction_values=mapping_values,
                notify=notification_calls.append, priority_action_active=lambda action:
                    source_callbacks.append(action) or action_results[action])

            observed_callbacks.clear()
            observed_notifications.clear()
            try:
                cpu.emu_start(ENTRY, oracle.stop, timeout=0, count=100000)
            except Exception as exc:
                raise AssertionError(f'case {case}: emulation fault at '
                    f'{cpu.reg_read(reg.UC_X86_REG_EIP):#x}, '
                    f'ESP={cpu.reg_read(reg.UC_X86_REG_ESP):#x}, '
                    f'EBP={cpu.reg_read(reg.UC_X86_REG_EBP):#x}, '
                    f'frame={[hex(x) for x in struct.unpack("<II", cpu.mem_read(frame, 8))]}') from exc
            if cpu.reg_read(reg.UC_X86_REG_EIP) != oracle.stop:
                raise AssertionError(f'case {case}: native slice failed to return')

            actual_latches = bytes(cpu.mem_read(EDGE_LATCHES, 13))
            actual_counter = struct.unpack('<I', cpu.mem_read(RING_COUNTER, 4))[0]
            actual_ring = list(struct.unpack('<32I', cpu.mem_read(RING_WORDS, 128)))
            actual_word = actual_ring[actual_counter & 31]
            actual_payload = bytes(cpu.mem_read(FRAME_OUTPUT, 5))
            if actual_counter != state.ring_counter or actual_ring != state.ring_words or \
                    actual_word != source[1] or actual_payload != state.notification_payload or \
                    observed_notifications != notification_calls:
                raise AssertionError(f'case {case}: state mismatch; native edge/ring/notify '
                    f'{actual_counter:#x}/{actual_word:#x}/'
                    f'{actual_payload.hex()}/{observed_notifications}, source '
                    f'{state.ring_counter:#x}/'
                    f'{source}/{state.notification_payload.hex()}/{notification_calls}; '
                    f'callback trace {observed_callbacks}; ring diffs '
                    f'{[(i, hex(a), hex(b)) for i,(a,b) in enumerate(zip(actual_ring, state.ring_words)) if a != b]}; '
                    f'directions {controller_ok}/{notification_suppressed}/'
                    f'{mapping_enabled}/{mapping_values}')
            # 460950's internal branches can short-circuit or dispatch twice;
            # compare callback trace too, which validates operation ordering.
            if observed_callbacks != source_callbacks:
                raise AssertionError(f'case {case}: callback order differs: '
                    f'{observed_callbacks} != {source_callbacks}')
        return cases
    finally:
        for hook_id in hook_ids:
            cpu.hook_del(hook_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    count = compare(args.executable, args.cases)
    print(f'action priority edges, 32-bit masks, ring insertion and notification '
          f'matched {count} original tail executions')


if __name__ == '__main__':
    main()
