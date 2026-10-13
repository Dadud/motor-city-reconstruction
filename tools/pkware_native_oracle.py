"""CPU-only comparison with the verified installed IMPLODE.DLL exports.

No DLL entry point, Windows imports, network calls or host DLL loading.
Only bounded memory callbacks used by implode/explode are supplied.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from client.pkware_dcl import explode

SOURCE_SHA256 = '349a62749766d1a8f9fe6e7bdd13b0cad67959c7454223557cae286c637c06d3'


class PKWareOracle:
    def __init__(self, dll):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
        from unicorn import x86_const
        data = Path(dll).read_bytes()
        if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
            raise ValueError('oracle requires exact verified IMPLODE.DLL')
        self.cpu = Uc(UC_ARCH_X86, UC_MODE_32)
        self.reg = x86_const
        pe = struct.unpack_from('<I', data, 60)[0]
        optional = pe+24
        base = struct.unpack_from('<I', data, optional+28)[0]
        size = struct.unpack_from('<I', data, optional+56)[0]
        self.cpu.mem_map(base, (size+4095)&~4095)
        headers = struct.unpack_from('<I', data, optional+60)[0]
        self.cpu.mem_write(base, data[:headers])
        sections = struct.unpack_from('<H', data, pe+6)[0]
        optional_size = struct.unpack_from('<H', data, pe+20)[0]
        for index in range(sections):
            section = optional+optional_size+index*40
            _, rva, raw_size, raw = struct.unpack_from('<4I', data, section+8)
            if raw_size:
                self.cpu.mem_write(base+rva, data[raw:raw+raw_size])
        export = base+struct.unpack_from('<I', data, optional+96)[0]
        _, _, _, _, _, _, _, count, functions, names, ordinals = struct.unpack(
            '<IIHH7I', bytes(self.cpu.mem_read(export, 40)))
        self.exports = {}
        for index in range(count):
            name_rva = self.u32(base+names+index*4)
            name = bytes(self.cpu.mem_read(base+name_rva, 64)).split(b'\0')[0].decode('ascii')
            ordinal = struct.unpack('<H', bytes(self.cpu.mem_read(base+ordinals+index*2, 2)))[0]
            self.exports[name] = base+self.u32(base+functions+ordinal*4)
        self.stub, self.work, self.stack = 0x70000000, 0x71000000, 0x72000000
        for address in (self.stub, self.work, self.stack):
            self.cpu.mem_map(address, 0x10000)
        self.read_callback, self.write_callback, self.stop = self.stub+0x100, self.stub+0x200, self.stub+0x300
        self.cpu.mem_write(self.read_callback, b'\xc3')
        self.cpu.mem_write(self.write_callback, b'\xc3')
        self.cpu.hook_add(UC_HOOK_CODE, self.callback, begin=self.read_callback, end=self.read_callback)
        self.cpu.hook_add(UC_HOOK_CODE, self.callback, begin=self.write_callback, end=self.write_callback)

    def u32(self, address):
        return struct.unpack('<I', bytes(self.cpu.mem_read(address, 4)))[0]

    def callback(self, cpu, address, size, unused):
        stack = cpu.reg_read(self.reg.UC_X86_REG_ESP)
        buffer, count_ptr = struct.unpack('<II', bytes(cpu.mem_read(stack+4, 8)))
        count = self.u32(count_ptr)
        if count > 65526:
            raise ValueError('native callback exceeds bound')
        if address == self.read_callback:
            part = self.source[self.position:self.position+count]
            if part:
                cpu.mem_write(buffer, part)
            self.position += len(part)
            cpu.reg_write(self.reg.UC_X86_REG_EAX, len(part))
        else:
            if len(self.output)+count > 65526:
                raise ValueError('native output exceeds bound')
            self.output.extend(cpu.mem_read(buffer, count))

    def run(self, name, source, *, mode=0, dictionary=1024):
        if not isinstance(source, bytes) or len(source) > 65526:
            raise ValueError('expected bounded oracle input')
        self.source, self.position, self.output = source, 0, bytearray()
        self.cpu.mem_write(self.work, bytes(0x10000))
        stack = self.stack+0x8000
        args = [self.stop, self.read_callback, self.write_callback, self.work, 0]
        if name == 'implode':
            self.cpu.mem_write(self.stack+0x100, struct.pack('<II', mode, dictionary))
            args += [self.stack+0x100, self.stack+0x104]
        self.cpu.mem_write(stack, struct.pack('<'+'I'*len(args), *args))
        self.cpu.reg_write(self.reg.UC_X86_REG_ESP, stack)
        self.cpu.emu_start(self.exports[name], self.stop, timeout=5_000_000, count=5_000_000)
        if self.cpu.reg_read(self.reg.UC_X86_REG_EIP) != self.stop:
            raise ValueError('native compression did not finish within limits')
        if self.cpu.reg_read(self.reg.UC_X86_REG_EAX) != 0:
            raise ValueError('native compression returned an error')
        return bytes(self.output)


def verify(dll):
    oracle = PKWareOracle(dll)
    cases = 0
    for mode in (0, 1):
        for dictionary in (1024, 2048, 4096):
            for source in (b'AIAIAIAIAIAIA', bytes(range(256)), b'garage car engine '*400):
                compressed = oracle.run('implode', source, mode=mode, dictionary=dictionary)
                if explode(compressed) != source or oracle.run('explode', compressed) != source:
                    raise ValueError('portable/native DCL comparison differs')
                cases += 1
    return {'matched_native_cases': cases, 'source_sha256': SOURCE_SHA256,
            'scope': 'CPU-emulated original exports with memory callbacks; no host DLL or network I/O'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dll')
    print(json.dumps(verify(parser.parse_args().dll), indent=2))
