"""Bounded CPU-only oracle for verified local dyno instruction ranges.

Optional Unicorn dependency. No original bytes are redistributed, no PE entry
point is launched, and no Windows imports or host services are implemented.
Results describe emulated execution, not original hardware/runtime behavior.
"""
import hashlib
from pathlib import Path
import struct

from client.dyno import _SOURCE_SHA256


class DynoOracle:
    def __init__(self, executable):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
        from unicorn import x86_const
        path = Path(executable)
        if path.stat().st_size > 32*1024*1024:
            raise ValueError('oracle executable exceeds supported size')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != _SOURCE_SHA256:
            raise ValueError('oracle requires exact verified executable')
        self.reg = x86_const
        pe = struct.unpack_from('<I', data, 60)[0]
        optional = pe+24
        image_size = struct.unpack_from('<I', data, optional+56)[0]
        base = struct.unpack_from('<I', data, optional+28)[0]
        count = struct.unpack_from('<H', data, pe+6)[0]
        optional_size = struct.unpack_from('<H', data, pe+20)[0]
        self.cpu = Uc(UC_ARCH_X86, UC_MODE_32)
        self.cpu.mem_map(base, (image_size+4095)&~4095)
        headers = struct.unpack_from('<I', data, optional+60)[0]
        self.cpu.mem_write(base, data[:headers])
        for index in range(count):
            section = optional+optional_size+index*40
            _, rva, raw_size, raw = struct.unpack_from('<4I', data, section+8)
            if raw_size:
                self.cpu.mem_write(base+rva, data[raw:raw+raw_size])
        self.stub = 0x70000000
        self.inputs = 0x71000000
        self.frame = 0x72008000
        self.stop = self.stub+0xfff0
        for address in (self.stub, self.inputs, 0x72000000):
            self.cpu.mem_map(address, 0x10000)
        self.reset_stub = self.stub+0xf000
        self.cpu.mem_write(self.reset_stub, b'\xdb\xe3')

    def _run(self, entry, stop, *, timeout=1_000_000, count=1_000_000):
        self.cpu.emu_start(entry, stop, timeout=timeout, count=count)
        if self.cpu.reg_read(self.reg.UC_X86_REG_EIP) != stop:
            raise ValueError('oracle did not finish within execution limits')

    def _reset(self):
        self._run(self.reset_stub, self.reset_stub+2, timeout=0, count=1)  # FNINIT
        self.cpu.reg_write(self.reg.UC_X86_REG_FPCW, 0x27f)
        self.cpu.reg_write(self.reg.UC_X86_REG_ESP, self.frame-0x1000)
        self.cpu.reg_write(self.reg.UC_X86_REG_EBP, self.frame)

    def power(self, base, exponent):
        """Original 0x69ba30/0x69ba52 helper; double arguments and output."""
        self._reset()
        code = b'\xdd\x05'+struct.pack('<I', self.inputs)
        code += b'\xdd\x05'+struct.pack('<I', self.inputs+8)
        call_end = self.stub+len(code)+5
        code += b'\xe8'+struct.pack('<i', 0x69ba30-call_end)
        code += b'\xdd\x1d'+struct.pack('<I', self.inputs+16)+b'\xc3'
        self.cpu.mem_write(self.stub, code)
        self.cpu.mem_write(self.inputs, struct.pack('<ddd', base, exponent, 0))
        stack = self.frame-0x1000
        self.cpu.mem_write(stack, struct.pack('<I', self.stop))
        self._run(self.stub, self.stop)
        return struct.unpack('<d', self.cpu.mem_read(self.inputs+16, 8))[0]

    def intake_correction(self, mode, rpm, flow_factor):
        """Execute REA 221 range 0x479c5e–0x479df6, before boost helper.

        Stack RPM at EBP-0xa8, result EBP-0x98; dyno mode/input at +0x6e/+0x70.
        This intentionally excludes boost and subsequent solver stages.
        """
        if type(mode) is not int or not 1 <= mode <= 6:
            raise ValueError('oracle intake mode must be within [1, 6]')
        self._reset()
        self.cpu.reg_write(self.reg.UC_X86_REG_ESI, self.inputs)
        self.cpu.mem_write(self.inputs+0x6e, struct.pack('<h', mode))
        self.cpu.mem_write(self.inputs+0x70, struct.pack('<f', flow_factor))
        self.cpu.mem_write(self.frame-0xa8, struct.pack('<f', rpm))
        self._run(0x479c5e, 0x479df6)
        return struct.unpack('<f', self.cpu.mem_read(self.frame-0x98, 4))[0]

    def exhaust_parameters(self, mode, rpm, flow_factor):
        """Bounded original valid-mode exhaust initialization branches."""
        if type(mode) is not int or not 1 <= mode <= 7:
            raise ValueError('oracle exhaust mode must be within [1, 7]')
        self._reset()
        self.cpu.reg_write(self.reg.UC_X86_REG_ESI, self.inputs)
        self.cpu.mem_write(self.inputs+0x7c, struct.pack('<f', flow_factor))
        self.cpu.mem_write(self.frame-0xa8, struct.pack('<f', rpm))
        entries = (0x479f42, 0x479f62, 0x479f82, 0x479fa2,
                   0x479fc2, 0x479fdf, 0x479ffc)
        self.cpu.ctl_remove_cache(0x479f42, 0x47a05b)
        self._run(entries[mode-1], 0x47a05b, timeout=0, count=1000)
        return tuple(struct.unpack('<f', self.cpu.mem_read(self.frame+offset, 4))[0]
                     for offset in (-0x94, -0x58, -0x54, -0x64))

    def charge_temperature(self, mode, rpm):
        self._reset()
        self.cpu.mem_write(self.frame-0x60, struct.pack('<f', mode))
        self.cpu.mem_write(self.frame-0xa8, struct.pack('<f', rpm))
        self._run(0x479bce, 0x479c5e, timeout=0, count=1000)
        return struct.unpack('<f', self.cpu.mem_read(self.frame-0xac, 4))[0]

    def intake_boundary(self, geometry, rpm, carb_capacity, carb_code, intake_mode, boost=0):
        self._reset()
        self.cpu.ctl_remove_cache(0x47a05b, 0x47a145)
        self.cpu.reg_write(self.reg.UC_X86_REG_ESI, self.inputs)
        self.cpu.mem_write(self.inputs+0xa4, struct.pack('<h', carb_capacity))
        self.cpu.mem_write(self.inputs+0x6e, struct.pack('<h', intake_mode))
        for offset, value in ((-0xb0, geometry.total_displacement), (-0xa8, rpm),
                              (-0xb4, 70), (-0xa4, boost)):
            self.cpu.mem_write(self.frame+offset, struct.pack('<f', value))
        self._run(0x479025 if carb_code == 2 else 0x47903a, 0x479050, timeout=0, count=100)
        self._run(0x479b29, 0x479b3f, timeout=0, count=100)
        self._run(0x479b60, 0x479b6c, timeout=0, count=100)
        self._run(0x47a05b, 0x47a0b0, timeout=0, count=100)
        return tuple(struct.unpack('<f', self.cpu.mem_read(self.frame+offset, 4))[0]
                     for offset in (-0x3c, -0x204, -0x20))

    def cycle_preparation(self, rpm, temperature, exhaust):
        self._reset()
        self.cpu.ctl_remove_cache(0x47a05b, 0x47a145)
        for offset, value in ((-0xa8, rpm), (-0xac, temperature), (-0x64, exhaust.rpm_exponent)):
            self.cpu.mem_write(self.frame+offset, struct.pack('<f', value))
        self._run(0x47a0b0, 0x47a145, timeout=0, count=10000)
        return tuple(struct.unpack('<f', self.cpu.mem_read(self.frame+offset, 4))[0]
                     for offset in (-0x224, -0x21c, -0x40))

    def exhaust_phase_factor(self, start_angle):
        self._reset()
        self.cpu.mem_write(self.frame-0x4c, struct.pack('<f', start_angle))
        self._run(0x479b6c, 0x479b81, timeout=0, count=100)
        return struct.unpack('<f', self.cpu.mem_read(self.frame-0x20c, 4))[0]

    def exhaust_wave_value(self, angle, start_angle, phase_factor, rpm, exhaust,
                           wave_scale, previous_value=0, boost=0):
        self._reset()
        fields = ((8, angle), (-0x4c, start_angle), (-0x20c, phase_factor),
                  (-0xa8, rpm), (-0x54, exhaust.reference_rpm), (-0x58, exhaust.amplitude),
                  (-0x94, exhaust.baseline), (-0x40, wave_scale), (-0x44, previous_value),
                  (-0xa4, boost))
        for offset, value in fields:
            self.cpu.mem_write(self.frame+offset, struct.pack('<f', value))
        self._run(0x47aa3d, 0x47aafd, timeout=0, count=1000)
        return struct.unpack('<f', self.cpu.mem_read(self.frame-0x44, 4))[0]

    def solver(self, inputs):
        """Run full 0x478ec0 on an explicit 1004-byte dyno input/output record.

        The caller owns validity of the assembled inputs. Completion alone
        does not prove the record corresponds to a valid stock engine.
        Returns original mutated bytes for evidence-bound field decoding.
        """
        if not isinstance(inputs, bytes) or len(inputs) != 1004:
            raise ValueError('oracle solver requires a 1004-byte dyno record')
        self._reset()
        self.cpu.mem_write(self.inputs, inputs)
        stack = self.frame-0x1000
        self.cpu.mem_write(stack, struct.pack('<II', self.stop, self.inputs))
        self._run(0x478ec0, self.stop, timeout=5_000_000, count=50_000_000)
        return bytes(self.cpu.mem_read(self.inputs, 1004))

    def solver_work_stages(self, inputs):
        """Capture stack inputs to 0x47b2b7 while running the full solver.

        Exact-address hook avoids replacing any original instructions. These
        observations validate the output stage, not portable integration.
        """
        from unicorn import UC_HOOK_CODE
        stages = []
        def capture(cpu, address, size, user_data):
            frame = cpu.reg_read(self.reg.UC_X86_REG_EBP)
            values = [struct.unpack('<f', cpu.mem_read(frame+offset, 4))[0]
                      for offset in (-0xa8, -0xc4, -0x50, -0x1e8,
                                     -0x3c, -0xa0, -0x220)]
            values[0] = int(values[0])
            stages.append(values)
        hook = self.cpu.hook_add(UC_HOOK_CODE, capture,
                                 begin=0x47b2b7, end=0x47b2b7)
        try:
            output = self.solver(inputs)
        finally:
            self.cpu.hook_del(hook)
        return output, stages

    def solver_geometry(self, inputs):
        """Execute initial solver instructions through geometry stores only."""
        if not isinstance(inputs, bytes) or len(inputs) != 1004:
            raise ValueError('oracle solver requires a 1004-byte dyno record')
        self._reset()
        self.cpu.mem_write(self.inputs, inputs)
        stack = self.frame-0x1000
        self.cpu.mem_write(stack, struct.pack('<II', self.stop, self.inputs))
        # Different observation endpoints can share a cached translation block.
        self.cpu.ctl_remove_cache(0x478ec0, 0x479af2)
        self._run(0x478ec0, 0x479023)
        frame = self.cpu.reg_read(self.reg.UC_X86_REG_EBP)
        return tuple(struct.unpack('<f', self.cpu.mem_read(frame+offset, 4))[0]
                     for offset in (-0xc8, -0x208, -0x1e8, -0xb8, -0xd0, -0xb0))

    def solver_valve_events(self, inputs):
        """Observe original event preparation before the first power call."""
        if not isinstance(inputs, bytes) or len(inputs) != 1004:
            raise ValueError('oracle solver requires a 1004-byte dyno record')
        self._reset()
        self.cpu.mem_write(self.inputs, inputs)
        stack = self.frame-0x1000
        self.cpu.mem_write(stack, struct.pack('<II', self.stop, self.inputs))
        self.cpu.ctl_remove_cache(0x478ec0, 0x479af2)
        self._run(0x478ec0, 0x4794eb)
        frame = self.cpu.reg_read(self.reg.UC_X86_REG_EBP)
        return tuple(struct.unpack('<f', self.cpu.mem_read(frame+offset, 4))[0]
                     for offset in (-0x1a8, -0x1d4, -0x4c, -0x1c4,
                                    -0x1ac, -0x1cc))

    def solver_flow_coefficients(self, inputs):
        """Observe normalized flow arrays before cam-profile construction."""
        if not isinstance(inputs, bytes) or len(inputs) != 1004:
            raise ValueError('oracle solver requires a 1004-byte dyno record')
        self._reset()
        self.cpu.mem_write(self.inputs, inputs)
        stack = self.frame-0x1000
        self.cpu.mem_write(stack, struct.pack('<II', self.stop, self.inputs))
        self.cpu.ctl_remove_cache(0x478ec0, 0x479af2)
        self._run(0x478ec0, 0x4798a4)
        frame = self.cpu.reg_read(self.reg.UC_X86_REG_EBP)
        scalar = struct.unpack('<f', self.cpu.mem_read(frame+8, 4))[0]
        first = struct.unpack('<10f', self.cpu.mem_read(frame-0x188, 40))
        second = struct.unpack('<10f', self.cpu.mem_read(frame-0x120, 40))
        return scalar, first, second

    def solver_cam_profiles(self, inputs):
        """Observe both cam-profile records before per-RPM integration."""
        if not isinstance(inputs, bytes) or len(inputs) != 1004:
            raise ValueError('oracle solver requires a 1004-byte dyno record')
        self._reset()
        self.cpu.mem_write(self.inputs, inputs)
        stack = self.frame-0x1000
        self.cpu.mem_write(stack, struct.pack('<II', self.stop, self.inputs))
        self.cpu.ctl_remove_cache(0x478ec0, 0x479af2)
        self._run(0x478ec0, 0x479af2)
        frame = self.cpu.reg_read(self.reg.UC_X86_REG_EBP)
        def read(offset):
            return struct.unpack('<f', self.cpu.mem_read(frame+offset, 4))[0]
        return (tuple(read(o) for o in (-0x1a4, -0x1a0, -0x19c,
                                       -0x198, -0x194, -0x190)),
                tuple(read(o) for o in (-0x1a4, -0x138, -0x134,
                                       -0x130, -0x12c, -0x128)))

    def valve_lift(self, profile, start_angle, angle, *, first=True):
        """Run only the active-window native lift branch on supplied fields."""
        self._reset()
        fields = (-0x1a4, -0x1a0, -0x19c, -0x198, -0x194, -0x190) if first else (
                  -0x1a4, -0x138, -0x134, -0x130, -0x12c, -0x128)
        for offset, value in zip(fields, profile):
            self.cpu.mem_write(self.frame+offset, struct.pack('<f', value))
        self.cpu.mem_write(self.frame+8, struct.pack('<f', angle))
        self.cpu.mem_write(self.frame+(-0x4c if first else -0x1a8),
                           struct.pack('<f', start_angle))
        self.cpu.mem_write(self.frame-8, struct.pack('<f', 1))
        self.cpu.mem_write(self.frame-0xbc, struct.pack('<f', 1))
        entry, stop = (0x47a63d, 0x47a709) if first else (0x47a17b, 0x47a256)
        self.cpu.ctl_remove_cache(entry, stop)
        self._run(entry, stop)
        store = self.stub+0x4000
        self.cpu.mem_write(store, b'\xdd\x1d'+struct.pack('<I', self.inputs+0x8000))
        self._run(store, store+6)
        return struct.unpack('<d', self.cpu.mem_read(self.inputs+0x8000, 8))[0]

    def interpolate_flow(self, lift, points, coefficients, *, first=True):
        """Observe native interpolation before correction/clamping."""
        self._reset()
        point_base, value_base, baseline = ((-0x160, -0x188, -0x18c) if first else
                                             (-0xf8, -0x120, -0x124))
        self.cpu.mem_write(self.frame+point_base, struct.pack('<10f', *points))
        self.cpu.mem_write(self.frame+value_base, struct.pack('<10f', *coefficients))
        self.cpu.mem_write(self.frame+baseline, struct.pack('<f', 1))
        load = self.stub+0x4100
        self.cpu.mem_write(self.inputs+0x8010, struct.pack('<d', lift))
        self.cpu.mem_write(load, b'\xdd\x05'+struct.pack('<I', self.inputs+0x8010))
        self._run(load, load+6)
        entry, stop = ((0x47a709, 0x47a9fe) if first else (0x47a256, 0x47a54b))
        self.cpu.ctl_remove_cache(entry, stop)
        self._run(entry, stop)
        store = self.stub+0x4000
        self.cpu.mem_write(store, b'\xdd\x1d'+struct.pack('<I', self.inputs+0x8000))
        self._run(store, store+6)
        return struct.unpack('<d', self.cpu.mem_read(self.inputs+0x8000, 8))[0]

    def pressure_correct_flow(self, coefficient, pressure_ratio):
        """Observe second-branch correction before valve-area multiplication."""
        self._reset()
        self.cpu.mem_write(self.frame-4, struct.pack('<f', pressure_ratio))
        self.cpu.mem_write(self.inputs+0x8010, struct.pack('<d', coefficient))
        load = self.stub+0x4100
        self.cpu.mem_write(load, b'\xdd\x05'+struct.pack('<I', self.inputs+0x8010))
        self._run(load, load+6)
        self.cpu.ctl_remove_cache(0x47a54b, 0x47a605)
        self._run(0x47a54b, 0x47a605)
        store = self.stub+0x4000
        self.cpu.mem_write(store, b'\xdd\x1d'+struct.pack('<I', self.inputs+0x8000))
        self._run(store, store+6)
        return struct.unpack('<d', self.cpu.mem_read(self.inputs+0x8000, 8))[0]

    def airflow_area(self, lift, points, coefficients, valve_size, *,
                     first=True, pressure_ratio=1):
        """Run interpolation, correction/clamping and native area store."""
        self._reset()
        point_base, value_base, baseline, size_offset, output = (
            (-0x160, -0x188, -0x18c, -0x1cc, -0x70) if first else
            (-0xf8, -0x120, -0x124, -0x1ac, -0x6c))
        self.cpu.mem_write(self.frame+point_base, struct.pack('<10f', *points))
        self.cpu.mem_write(self.frame+value_base, struct.pack('<10f', *coefficients))
        self.cpu.mem_write(self.frame+baseline, struct.pack('<f', 1))
        self.cpu.mem_write(self.frame+size_offset, struct.pack('<f', valve_size))
        self.cpu.mem_write(self.frame-4, struct.pack('<f', pressure_ratio))
        self.cpu.mem_write(self.inputs+0x8010, struct.pack('<d', lift))
        load = self.stub+0x4100
        self.cpu.mem_write(load, b'\xdd\x05'+struct.pack('<I', self.inputs+0x8010))
        self._run(load, load+6, timeout=0, count=1)
        entry, stop = (0x47a709, 0x47aa3d) if first else (0x47a256, 0x47a618)
        self.cpu.ctl_remove_cache(entry, stop)
        self._run(entry, stop, timeout=0, count=1000)
        return struct.unpack('<f', self.cpu.mem_read(self.frame+output, 4))[0]

    def initial_cylinder_state(self, geometry, stroke_inches, start_angle, pressure=44.1):
        """Observe native cylinder initialization, including original trig stores."""
        self._reset()
        self.cpu.reg_write(self.reg.UC_X86_REG_ESI, self.inputs)
        self.cpu.mem_write(self.inputs+0x7a, struct.pack('<h', 1))
        fields = {-0xc4: stroke_inches, -0xc8: geometry.bore_squared,
                  -0xd0: geometry.rod_length, -0xb8: geometry.clearance_volume,
                  -0x4c: start_angle, -8: pressure}
        for offset, value in fields.items():
            self.cpu.mem_write(self.frame+offset, struct.pack('<f', value))
        self.cpu.ctl_remove_cache(0x479b3f, 0x479b60)
        self._run(0x479b3f, 0x479b60, timeout=0, count=100)
        self._run(0x479e4d, 0x479f35, timeout=0, count=10000)
        return tuple(struct.unpack('<f', self.cpu.mem_read(self.frame+offset, 4))[0]
                     for offset in (-8, -0x1c, -0x40, -0x88, -0x28, -0x48, -0x1d8))

    def builder_inputs(self, assembled):
        """Run 0x46d1d0 up to its first solver call at 0x46d707 (REA 238).

        Caller supplies an explicit assembled engine structure. This compares
        the dyno builder, not earlier component validation/assembly routines.
        No torque solver or finalizer is executed by this method.
        """
        if not isinstance(assembled, bytes) or len(assembled) != 0x820:
            raise ValueError('oracle builder requires a 0x820-byte assembled structure')
        self._reset()
        self.cpu.mem_write(0x72000000, bytes(0x10000))
        address = self.inputs+0x2000
        self.cpu.mem_write(address, assembled)
        stack = self.frame-0x1000
        self.cpu.mem_write(stack, struct.pack('<II', self.stop, address))
        self._run(0x46d1d0, 0x46d707)
        pointer = struct.unpack('<I', self.cpu.mem_read(self.cpu.reg_read(self.reg.UC_X86_REG_ESP), 4))[0]
        if not 0x72000000 <= pointer <= 0x72010000-1004:
            raise ValueError('native builder returned a dyno pointer outside stack memory')
        return bytes(self.cpu.mem_read(pointer, 1004))
