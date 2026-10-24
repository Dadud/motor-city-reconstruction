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

    def random_next(self, words):
        """Run the original shared 0x6f0fa0 generator on six supplied words."""
        if (len(words) != 6 or any(type(word) is not int or not 0 <= word <= 0xffffffff
                                   for word in words)):
            raise ValueError('random oracle requires six unsigned 32-bit words')
        self._reset()
        addresses = (0x8c89d0, 0x8c89d4, 0x8c89d8,
                     0x8c89dc, 0x8c89e0, 0x8c89e4)
        for address, word in zip(addresses, words):
            self.cpu.mem_write(address, struct.pack('<I', word))
        self.call(0x6f0fa0)
        result = tuple(struct.unpack('<I', self.cpu.mem_read(address, 4))[0]
                       for address in addresses)
        return self.cpu.reg_read(self.reg.UC_X86_REG_EAX), result

    def sky_material_indices(self):
        """Capture the enabled 25x25 index table emitted by 0x4943f0."""
        self._reset()
        block = bytearray(0xc138)
        struct.pack_into('<I', block, 0xc0c4, 1)
        struct.pack_into('<f', block, 0xc120, 0.125)
        self.cpu.mem_write(self.inputs, bytes(block))
        stack = self.frame-0x1000
        self.cpu.mem_write(stack, struct.pack('<I', self.stop))
        self.cpu.reg_write(self.reg.UC_X86_REG_ESP, stack)
        self.cpu.reg_write(self.reg.UC_X86_REG_EBP, self.frame)
        code = b'\x68'+struct.pack('<I', self.inputs)+b'\xe8'+b'\0'*4+b'\x83\xc4\x04\xc3'
        call_at = self.stub+5
        code = code[:6]+struct.pack('<i', 0x4943f0-(call_at+5))+code[10:]
        self.cpu.mem_write(self.stub, code)
        if hasattr(self.cpu, 'ctl_flush_tb'):
            self.cpu.ctl_flush_tb()
        self._run(self.stub, self.stop, timeout=0, count=100_000_000)
        return bytes(self.cpu.mem_read(self.inputs+0x9e70, 25*0x138))

    def sky_material_parameters(self, *, height_bound, random_modulus,
                                 random_divisor, random_reciprocal,
                                 column_scale, row_scale,
                                 angle_degrees, radial_distance):
        """Run the original 0x494dc0 sky parameter normalization helper."""
        self._reset()
        block = bytearray(0xc138)
        for offset, value in ((0xc0c8, height_bound),
                              (0xc0d0, random_modulus),
                              (0xc0d8, random_divisor),
                              (0xc130, radial_distance),
                              (0xc134, angle_degrees)):
            struct.pack_into('<i', block, offset, value)
        for offset, value in ((0xc0dc, random_reciprocal),
                              (0xc118, column_scale), (0xc11c, row_scale)):
            struct.pack_into('<f', block, offset, value)
        self.cpu.mem_write(self.inputs, bytes(block))
        self.call(0x494dc0, (self.inputs,), instruction_limit=1000)
        block = bytes(self.cpu.mem_read(self.inputs, len(block)))
        return (struct.unpack_from('<i', block, 0xc0d0)[0],
                struct.unpack_from('<f', block, 0xc0dc)[0],
                struct.unpack_from('<f', block, 0xc118)[0],
                struct.unpack_from('<f', block, 0xc11c)[0],
                struct.unpack_from('<f', block, 0xc0e0)[0],
                struct.unpack_from('<f', block, 0xc0e4)[0])

    def vector_length3(self, values):
        """Capture 0x6f1210's x87 result as a binary32 output word."""
        if len(values) != 3:
            raise ValueError('vector length oracle requires three values')
        self._reset()
        self.cpu.mem_write(self.inputs, struct.pack('<3f', *values))
        code = (b'\x68'+struct.pack('<I', self.inputs)+b'\xe8'+b'\0'*4+
                b'\x83\xc4\x04\xd9\x1d'+struct.pack('<I', self.inputs+16)+b'\xc3')
        call_at = self.stub+5
        code = code[:6]+struct.pack('<i', 0x6f1210-(call_at+5))+code[10:]
        self.cpu.mem_write(self.stub, code)
        stack = self.frame-0x1000
        self.cpu.mem_write(stack, struct.pack('<I', self.stop))
        self.cpu.reg_write(self.reg.UC_X86_REG_ESP, stack)
        self.cpu.reg_write(self.reg.UC_X86_REG_EBP, self.frame)
        if hasattr(self.cpu, 'ctl_flush_tb'):
            self.cpu.ctl_flush_tb()
        self._run(self.stub, self.stop, timeout=0, count=1000)
        return struct.unpack('<f', self.cpu.mem_read(self.inputs+16, 4))[0]

    def normalized_cross3(self, left, right):
        """Run the original 0x6f10d0 cross-and-normalize helper."""
        if len(left) != 3 or len(right) != 3:
            raise ValueError('native cross product requires two 3D vectors')
        self._reset()
        output = self.inputs+0x100
        self.cpu.mem_write(self.inputs, struct.pack('<6f', *(tuple(left)+tuple(right))))
        self.call(0x6f10d0, (self.inputs, self.inputs+12, output),
                  instruction_limit=2000)
        return struct.unpack('<3f', self.cpu.mem_read(output, 12))

    def track_cross_section(self, object_transform, basis, vertical_offset,
                             origin_scale, view_reference, world_origin,
                             radius, angle_offset):
        """Run the native 0x495240 track cross-section builder."""
        if len(object_transform) != 14 or any(len(v) != 3 for v in
                (basis, view_reference, world_origin)):
            raise ValueError('track cross-section inputs have invalid dimensions')
        self._reset()
        obj, output, angle = self.inputs+0x1000, self.inputs+0x2000, self.inputs+0x3000
        raw = bytearray(0x38)
        struct.pack_into('<14f', raw, 0, *object_transform)
        self.cpu.mem_write(obj, bytes(raw))
        self.cpu.mem_write(0x8915a8, struct.pack('<3f', *world_origin))
        self.cpu.mem_write(0x8915b8, struct.pack('<3f', *basis))
        self.cpu.mem_write(0x9c77b0, struct.pack('<3f', *view_reference))
        self.cpu.mem_write(0x9aefe0, struct.pack('<f', radius))
        float_word = lambda value: struct.unpack('<I', struct.pack('<f', value))[0]
        self.call(0x495240, (obj, float_word(vertical_offset), float_word(origin_scale),
                             output, angle, float_word(angle_offset)),
                  instruction_limit=100_000)
        result = struct.unpack('<9f', self.cpu.mem_read(output, 36))
        angle_result, = struct.unpack('<f', self.cpu.mem_read(angle, 4))
        return self.cpu.reg_read(self.reg.UC_X86_REG_EAX), result, angle_result

    def track_grid_strips(self, object_transform, basis, height, origin_scale,
                          view_reference, world_origin, radius, angle_offset=0.0):
        """Run native track generator 0x495800 and capture both 17-point strips."""
        if len(object_transform) != 14 or any(len(v) != 3 for v in
                (basis, view_reference, world_origin)):
            raise ValueError('track strip inputs have invalid dimensions')
        self._reset()
        obj, angle = self.inputs+0x1000, self.inputs+0x2000
        first, second = self.inputs+0x3000, self.inputs+0x4000
        raw = bytearray(0x38)
        struct.pack_into('<14f', raw, 0, *object_transform)
        self.cpu.mem_write(obj, bytes(raw))
        self.cpu.mem_write(0x8915a8, struct.pack('<3f', *world_origin))
        self.cpu.mem_write(0x8915b8, struct.pack('<3f', *basis))
        self.cpu.mem_write(0x9c77b0, struct.pack('<3f', *view_reference))
        self.cpu.mem_write(0x9aefe0, struct.pack('<f', radius))
        word = lambda v: struct.unpack('<I', struct.pack('<f', v))[0]
        self.call(0x495800, (obj, word(height), word(origin_scale), angle,
                             first, second, word(angle_offset)),
                  instruction_limit=100_000)
        first_points = struct.unpack('<51f', self.cpu.mem_read(first, 204))
        second_points = struct.unpack('<51f', self.cpu.mem_read(second, 204))
        angle_result, = struct.unpack('<f', self.cpu.mem_read(angle, 4))
        return (self.cpu.reg_read(self.reg.UC_X86_REG_EAX),
                tuple(tuple(first_points[i:i+3]) for i in range(0, 51, 3)),
                tuple(tuple(second_points[i:i+3]) for i in range(0, 51, 3)),
                angle_result)

    def wrap_track_turn(self, turn):
        """Run the native in-place angle wrapper at 0x4b70f0."""
        self._reset()
        self.cpu.mem_write(self.inputs, struct.pack('<f', turn))
        self.call(0x4b70f0, (self.inputs,), instruction_limit=100_000)
        return struct.unpack('<f', self.cpu.mem_read(self.inputs, 4))[0]

    def linear_vector_sequence(self, count, first, second):
        """Run 0x4954c0 and return its complete count-point output buffer."""
        if type(count) is not int or not 2 <= count <= 65536:
            raise ValueError('native point count must be within [2, 65536]')
        if len(first) != 3 or len(second) != 3:
            raise ValueError('native point sequence requires two 3D points')
        self._reset()
        output = self.inputs+0x1000
        self.cpu.mem_write(self.inputs, struct.pack('<6f', *(tuple(first)+tuple(second))))
        self.call(0x4954c0, (count, self.inputs, output), instruction_limit=10000)
        return tuple(tuple(row) for row in struct.iter_unpack(
            '<3f', self.cpu.mem_read(output, count*12)))

    def blend_track_color(self, argb, base_argb, divisor, *, bypass=False):
        """Run the original 0x4956e0 track color transform."""
        if (type(argb) is not int or not 0 <= argb <= 0xffffffff or
                type(base_argb) is not int or not 0 <= base_argb <= 0xffffffff):
            raise ValueError('colors must be unsigned 32-bit ARGB words')
        if type(bypass) is not bool:
            raise ValueError('bypass must be a boolean')
        self._reset()
        self.cpu.mem_write(0x00a55484, struct.pack('<I', int(bypass)))
        self.cpu.mem_write(0x009af064, struct.pack('<I', base_argb))
        self.cpu.mem_write(0x009af068, struct.pack('<f', divisor))
        self.call(0x4956e0, (argb,), instruction_limit=2000)
        return self.cpu.reg_read(self.reg.UC_X86_REG_EAX)

    def sky_material_height_grid(self, stage, *, upper_bound, modulus, angle,
                                 row_scale, column_scale, random_state,
                                 base_offset=0.0, amplitude=0.0,
                                 color_scale=1.0, invert=False,
                                 texture_rgba=None):
        """Capture the kernel's local 26x26 grid at a specific verified stage."""
        stops = {'raw': 0x4945f5, 'normalized': 0x49466f,
                 'smoothed': 0x49480e, 'output': 0x49492a}
        if stage not in stops:
            raise ValueError('unknown sky material stage')
        if (len(random_state) != 6 or any(type(word) is not int or not 0 <= word <= 0xffffffff
                                          for word in random_state)):
            raise ValueError('random state must contain six unsigned words')
        self._reset()
        block = bytearray(0xc138)
        struct.pack_into('<I', block, 0xc0c4, 1)
        struct.pack_into('<i', block, 0xc0c8, upper_bound)
        struct.pack_into('<I', block, 0xc0d0, modulus)
        struct.pack_into('<f', block, 0xc0fc, base_offset)
        struct.pack_into('<f', block, 0xc100, amplitude)
        struct.pack_into('<f', block, 0xc0cc, color_scale)
        struct.pack_into('<f', block, 0xc118, column_scale)
        struct.pack_into('<f', block, 0xc11c, row_scale)
        struct.pack_into('<f', block, 0xc120, angle)
        struct.pack_into('<I', block, 0xc124, int(invert))
        if texture_rgba is not None:
            if not isinstance(texture_rgba, bytes) or len(texture_rgba) != 26*26*4:
                raise ValueError('texture override must contain 676 RGBA pixels')
            struct.pack_into('<I', block, 0xc12c, 1)
            block[0x93e0:0x93e0+len(texture_rgba)] = texture_rgba
        self.cpu.mem_write(self.inputs, bytes(block))
        for address, word in zip((0x8c89d0, 0x8c89d4, 0x8c89d8,
                                  0x8c89dc, 0x8c89e0, 0x8c89e4), random_state):
            self.cpu.mem_write(address, struct.pack('<I', word))
        stack = self.frame
        self.cpu.mem_write(stack, struct.pack('<II', self.stop, self.inputs))
        self.cpu.reg_write(self.reg.UC_X86_REG_ESP, stack)
        self.cpu.reg_write(self.reg.UC_X86_REG_EBP, self.frame)
        if hasattr(self.cpu, 'ctl_flush_tb'):
            self.cpu.ctl_flush_tb()
        self._run(0x4943f0, stops[stage], timeout=0, count=100_000_000)
        if stage == 'output':
            return bytes(self.cpu.mem_read(self.inputs, len(block)))
        frame = self.cpu.reg_read(self.reg.UC_X86_REG_EBP)
        raw = bytes(self.cpu.mem_read(frame-0xae0, 26*26*4))
        return struct.unpack('<676f', raw)

    def call(self, entry, arguments=(), *, tail=b'', cleanup=None,
             this_pointer=None, instruction_limit=4096):
        """Call a cdecl routine in the original with planted arguments.

        Arguments are given in source order: the first argument ends up at
        [EBP+8], which is where every original reads it. That is the opposite
        of the push order, and getting it backwards is the single easiest way
        to produce an oracle that passes for the wrong reason.

        `this_pointer` sets ECX first, for member routines that read their
        state through the register instead of a stack argument.

        `tail` runs after the call and before the return, which is how a result
        is captured. `cleanup` defaults to dropping every pushed argument, which
        is what cdecl requires.

        `instruction_limit` keeps each emulated call bounded; complex routines
        may explicitly request up to ten million instructions instead of 4096.

        Verified against the original for integer results: `call(0x405900)`
        reproduces both branches of the global singleton accessor exactly.
        **Float results are not reliable on this emulator.** A routine whose
        result travels in ST0 does not survive the round trip: FILD stores 0.0
        for a nonzero operand, and a post-call FSTP through `tail` yields
        garbage, while the original's own stored results read back correctly.
        Float-returning routines need the original's own store, as `power`
        does, or no oracle at all. Capture integers here and leave floats to
        the routine's own memory writes.
        """
        if type(instruction_limit) is not int or not 1 <= instruction_limit <= 10_000_000:
            raise ValueError('oracle instruction limit must be between 1 and 10000000')
        self._reset()
        # The stop address is planted below the pushed arguments: after cdecl
        # cleanup drops them, ESP is back to `stack` and the stub's final RET
        # consumes the planted address from there.
        stack = self.frame-0x1000
        self.cpu.mem_write(stack, struct.pack('<I', self.stop))
        self.cpu.reg_write(self.reg.UC_X86_REG_ESP, stack)
        self.cpu.reg_write(self.reg.UC_X86_REG_EBP, self.frame)
        if this_pointer is not None:
            self.cpu.reg_write(self.reg.UC_X86_REG_ECX,
                               this_pointer & 0xffffffff)
        prologue = b''.join(b'\x68'+struct.pack('<I', value & 0xffffffff)
                            for value in reversed(list(arguments)))
        call_at = self.stub+len(prologue)
        if cleanup is None:
            # Nothing was pushed, so nothing is dropped: emitting `add esp,0`
            # would be dead code in every no-argument stub.
            cleanup = (b'\x83\xc4'+struct.pack('<B', 4*len(arguments))
                       if arguments else b'')
        body = (prologue + b'\xe8' + b'\x00'*4 + tail + cleanup + b'\xc3')
        # The displacement is relative to the end of the call instruction.
        relative = entry-(call_at+5)
        body = body[:len(prologue)+1]+struct.pack('<i', relative)+body[len(prologue)+5:]
        self.cpu.mem_write(self.stub, body)
        # Unicorn caches translated blocks by guest address. The stub is
        # rewritten at the same address on every call, so without this flush
        # the second routine in a process executes the first routine's cached
        # translation and every result after the first call is wrong.
        if hasattr(self.cpu, 'ctl_flush_tb'):
            self.cpu.ctl_flush_tb()
        self._run(self.stub, self.stop, timeout=0, count=instruction_limit)
        return self

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

    def intake_mass_exchange(self, cylinder_pressure, cylinder_temperature, intake_pressure,
                             intake_temperature, area, rpm, previous=None):
        self._reset()
        self.cpu.ctl_remove_cache(0x47abe4, 0x47ae8f)
        feedback = (0, 0, 0, 0) if previous is None else (
            previous.pressure_ratio, previous.flow_term, previous.thermal_root, previous.density_term)
        fields = ((-8, cylinder_pressure), (-0x1c, cylinder_temperature),
                  (-0xbc, intake_pressure), (-0xac, intake_temperature), (-0x6c, area),
                  (-0xa8, rpm), (-0x2c, 0), (-0x34, 0), (-0x200, 0),
                  (-0x14, feedback[0]), (-0x1b4, feedback[1]),
                  (-0x1d0, feedback[2]), (-0x1f0, feedback[3]))
        for offset, value in fields:
            self.cpu.mem_write(self.frame+offset, struct.pack('<f', value))
        self._run(0x47abe4, 0x47ad3b, timeout=0, count=10000)
        return tuple(struct.unpack('<f', self.cpu.mem_read(self.frame+offset, 4))[0]
                     for offset in (-0x2c, -0x14, -0x1b4, -0x1d0, -0x1f0))

    def intake_pressure_feedback(self, boundary_pressure, area, valve_scale, previous, wave=0):
        self._reset()
        self.cpu.ctl_remove_cache(0x47ab69, 0x47ae8f)
        fields = ((-0x20, boundary_pressure), (-0x6c, area), (-0x214, valve_scale),
                  (-0x78, wave), (-0x1b4, previous.flow_term),
                  (-0x1d0, previous.thermal_root), (-0x1f0, previous.density_term))
        for offset, value in fields:
            self.cpu.mem_write(self.frame+offset, struct.pack('<f', value))
        self._run(0x47ab69, 0x47abe4, timeout=0, count=10000)
        return struct.unpack('<f', self.cpu.mem_read(self.frame-0xbc, 4))[0]

    def exhaust_mass_transfer(self, cylinder_pressure, cylinder_temperature, exhaust_pressure, area, rpm):
        self._reset()
        self.cpu.ctl_remove_cache(0x47abe4, 0x47ae8f)
        for offset, value in ((-8, cylinder_pressure), (-0x1c, cylinder_temperature),
                              (-0x44, exhaust_pressure), (-0x70, area), (-0xa8, rpm), (-0x1bc, 0)):
            self.cpu.mem_write(self.frame+offset, struct.pack('<f', value))
        self._run(0x47ad3b, 0x47ae8f, timeout=0, count=10000)
        return struct.unpack('<f', self.cpu.mem_read(self.frame-0x18, 4))[0]

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

    def solver_mass_exchange_stages(self, inputs, *, stride=64, per_rpm=32):
        """Bounded per-RPM samples from original intake/exhaust loop execution.

        Exact-address hooks observe instructions without replacing them.
        Captures input/output pairs; does not provide a portable full solver.
        """
        from unicorn import UC_HOOK_CODE
        if type(stride) is not int or stride < 1 or type(per_rpm) is not int or not 1 <= per_rpm <= 128:
            raise ValueError('invalid mass-exchange sampling bounds')
        rows, counts, selected = [], {}, {}
        pending = None
        boundary_inputs = None

        def read(cpu, frame, offsets):
            return tuple(struct.unpack('<f', cpu.mem_read(frame+offset, 4))[0] for offset in offsets)

        def capture(cpu, address, size, user_data):
            nonlocal pending, boundary_inputs
            frame = cpu.reg_read(self.reg.UC_X86_REG_EBP)
            if address == 0x47ab69:
                boundary_inputs = dict(inputs=read(cpu, frame, (-0x20, -0x6c, -0x214, -0x78)),
                    previous=read(cpu, frame, (-0x1b4, -0x1d0, -0x1f0)))
            elif address == 0x47abe4:
                rpm = read(cpu, frame, (-0xa8,))[0]
                count = counts.get(rpm, 0)
                counts[rpm] = count+1
                pending = None
                if count % stride == 0 and selected.get(rpm, 0) < per_rpm:
                    selected[rpm] = selected.get(rpm, 0)+1
                    pending = dict(intake_inputs=read(cpu, frame, (-8, -0x1c, -0xbc, -0xac, -0x6c, -0xa8)),
                        feedback=read(cpu, frame, (-0x14, -0x1b4, -0x1d0, -0x1f0)),
                        pressure_feedback=boundary_inputs)
            elif address == 0x47ad3b and pending is not None:
                pending['intake_output'] = read(cpu, frame, (-0x2c, -0x14, -0x1b4, -0x1d0, -0x1f0))
                pending['exhaust_inputs'] = read(cpu, frame, (-8, -0x1c, -0x44, -0x70, -0xa8))
            elif address == 0x47ae8f and pending is not None:
                pending['exhaust_output'] = read(cpu, frame, (-0x18,))[0]
                rows.append(pending)
                pending = None

        hooks = [self.cpu.hook_add(UC_HOOK_CODE, capture, begin=address, end=address)
                 for address in (0x47ab69, 0x47abe4, 0x47ad3b, 0x47ae8f)]
        try:
            self.cpu.ctl_remove_cache(0x478ec0, 0x47b500)
            output = self.solver(inputs)
        finally:
            for hook in hooks:
                self.cpu.hook_del(hook)
        return output, rows, counts

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
        # A previous full finalizer call may cache a block spanning the bounded
        # stop address. Recompile its blocks for this entry-to-solver boundary.
        self.cpu.ctl_remove_cache(0x46d1d0,0x46dbd9)
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
