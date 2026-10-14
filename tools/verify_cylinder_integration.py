"""Compare each recovered integration step against the original bounded solver.

No helpers are replaced: the original power helper and boost routine execute in
Unicorn. Input records are supplied locally and are never bundled with this tool.
"""
import argparse
from dataclasses import astuple
import json
from pathlib import Path
import struct
from client.cylinder_integration import (IntegrationState, IntegrationInputs, integrate_crank_step,
    carry_cycle_pressure, crank_step_size)
from tools.native_oracle import DynoOracle

STATE_OFFSETS = (-8, -0x1c, -0x48, -0x1e4, -0x1dc, -0x1b0,
                 -0x1f8, -0x1f4, -0x1fc, -0x50)
INPUT_OFFSETS = (8, -0x34, -0xa8, -0x1b8, -0xd0, -0x88, -0x28, -0xb8,
                 -0xcc, -0x208, -0x2c, -0x18, -0xbc, -0x44, -0x224,
                 -0x1c8, -0x7c, -0x80)


def main():
    from unicorn import UC_HOOK_CODE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('record', type=Path, help='private capture JSON containing input_hex')
    args = parser.parse_args()
    oracle = DynoOracle(args.executable)
    record = bytes.fromhex(json.loads(args.record.read_text())['input_hex'])
    pending = None
    count = 0
    mismatch_count = 0
    rpms = set()
    expected_carry = None
    carry_checks = 0
    mismatches = []
    def read(frame, offsets):
        return tuple(struct.unpack('<f', oracle.cpu.mem_read(frame+o,4))[0] for o in offsets)
    def capture(cpu, address, size, data):
        nonlocal pending, count, mismatch_count, expected_carry, carry_checks
        frame = cpu.reg_read(oracle.reg.UC_X86_REG_EBP)
        if address == 0x479e2a:
            knot = cpu.reg_read(oracle.reg.UC_X86_REG_EDI)
            previous,end = read(frame,(-8,-0x1e0))
            expected_carry = carry_cycle_pressure(knot,previous,end)
            return
        if address == 0x479e4d:
            if read(frame,(-8,))[0] != expected_carry:
                raise AssertionError('pressure carryover differs')
            carry_checks += 1
            return
        if address == 0x479bce:
            rpm,step = read(frame,(-0xa8,-0x34))
            if step != crank_step_size(int(rpm)):
                raise AssertionError('crank step differs')
            return
        if address == 0x47ae8f:
            state = IntegrationState(*read(frame, STATE_OFFSETS))
            inputs = IntegrationInputs(*read(frame, INPUT_OFFSETS))
            pending = integrate_crank_step(state, inputs)
            rpms.add(inputs.rpm)
        elif pending is not None:
            extra_offsets = (8, -0xc, -0x1e4, -0x1dc, -0x1b0, -0x84, -0x8c)
            expected = read(frame, STATE_OFFSETS+extra_offsets)
            actual = astuple(pending.state)+(pending.angle,pending.volume,pending.pressure_rate,
                pending.temperature_rate,pending.mass_rate,pending.intake_specific_energy,pending.exhaust_specific_energy)
            count += 1
            if actual != expected:
                mismatch_count += 1
            if actual != expected and len(mismatches) < 10:
                mismatches.append(dict(step=count, differences=[(hex(o),a,e) for o,a,e in zip(STATE_OFFSETS+extra_offsets,actual,expected) if a != e]))
            pending = None
    hooks = [oracle.cpu.hook_add(UC_HOOK_CODE,capture,begin=a,end=a) for a in (0x47ae8f,0x47b285,0x479e2a,0x479e4d,0x479bce)]
    try:
        oracle.cpu.ctl_remove_cache(0x478ec0,0x47b500)
        original_output = oracle.solver(record)
    finally:
        for hook in hooks:
            oracle.cpu.hook_del(hook)
    # A second complete run feeds portable outputs back into the next original
    # valve stage, so rounding drift cannot hide behind independent snapshots.
    replay = DynoOracle(args.executable)
    def portable_stage(cpu, address, size, data):
        frame = cpu.reg_read(replay.reg.UC_X86_REG_EBP)
        def fields(offsets):
            return tuple(struct.unpack('<f',cpu.mem_read(frame+o,4))[0] for o in offsets)
        result = integrate_crank_step(IntegrationState(*fields(STATE_OFFSETS)),
                                      IntegrationInputs(*fields(INPUT_OFFSETS)))
        state = IntegrationState(*fields(STATE_OFFSETS))
        inputs = IntegrationInputs(*fields(INPUT_OFFSETS))
        # Remaining scratch writes include the end-pressure carryover slot.
        from client.dyno_solver import _f32
        import math
        radians = _f32((inputs.angle+inputs.step)*_f32(.017453292))
        scratch = {-0x1e0: result.state.pressure, -0x210: state.pressure,
                   -0x1c0: inputs.crank_radius, -0x68: inputs.crank_radius,
                   -0x1ec: inputs.piston_area, -0x90: radians,
                   -0x30: _f32(inputs.crank_radius/inputs.rod_length*math.sin(radians))}
        for offset,value in scratch.items():
            cpu.mem_write(frame+offset,struct.pack('<f',value))
        values = astuple(result.state)+(result.angle,result.volume,result.pressure_rate,
            result.temperature_rate,result.mass_rate,result.intake_specific_energy,result.exhaust_specific_energy)
        offsets = STATE_OFFSETS+(8,-0xc,-0x1e4,-0x1dc,-0x1b0,-0x84,-0x8c)
        for offset,value in zip(offsets,values):
            cpu.mem_write(frame+offset,struct.pack('<f',value))
        cpu.reg_write(replay.reg.UC_X86_REG_EIP,0x47b285)
    hook = replay.cpu.hook_add(UC_HOOK_CODE,portable_stage,begin=0x47ae8f,end=0x47ae8f)
    try:
        replay_output = replay.solver(record)
    finally:
        replay.cpu.hook_del(hook)
    if original_output != replay_output:
        raise AssertionError('portable integration replay changed final solver record')
    print(json.dumps(dict(portable_feedback_replay_record_equal=True,carry_checks=carry_checks,steps=count, fields_per_step=17, exact_fields=(count-mismatch_count)*17, rpm_knots=sorted(rpms), mismatch_count=mismatch_count, mismatches=mismatches),indent=2))
    if mismatches:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
