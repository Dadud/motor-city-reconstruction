"""Compare 0x457780 and the six-contact force pass with the installed client."""
import argparse
import random
import subprocess
import struct
from pathlib import Path

from client.contact_force import contact_forces_step, contact_response
from tools.native_oracle import DynoOracle


def verify(executable,native_runner=None):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    owner = 0x0092C478
    force_ptr, point_ptr, normal_ptr = 0x00950000, 0x00950100, 0x00950200
    linear_out, angular_out = 0x00950300, 0x00950400
    rng = random.Random(0x51FC00)
    direct_cases = []
    for direction in range(3):
        record = bytearray(0x4f8)
        struct.pack_into('<f',record,0x54,1.0+direction)
        rotation=((1,0,0,0,1,0,0,0,1) if direction==0 else
                  (0,-1,0,1,0,0,0,0,1) if direction==1 else
                  (0,0,1,0,1,0,-1,0,0))
        struct.pack_into('<9f',record,0x78,*rotation)
        struct.pack_into('<9f',record,0x9c,*rotation)
        struct.pack_into('<3f',record,0x2fc,1,2,4)
        axes=((1,0,0),(0,1,0),(0,0,1))
        axis=axes[direction]
        force=tuple(-2.0*x for x in axis)
        point=tuple(float(x) for x in axes[(direction+1)%3])
        direct_cases.append((record,force,point,axis))
    for _ in range(128):
        record=bytearray(0x4f8)
        for offset in (0x54,0x78,0x7c,0x80,0x84,0x88,0x8c,0x90,0x94,0x98,
                       0x9c,0xa0,0xa4,0xa8,0xac,0xb0,0xb4,0xb8,0xbc,
                       0x2fc,0x300,0x304):
            struct.pack_into('<f',record,offset,rng.uniform(-2,2))
        force=tuple(rng.uniform(-2,2) for _ in range(3))
        point=tuple(rng.uniform(-2,2) for _ in range(3))
        normal=tuple(rng.uniform(-1,1) for _ in range(3))
        direct_cases.append((record,force,point,normal))

    # Include simple values whose full helper result exercises both its
    # approaching and separating normal-velocity branches without ambiguity.
    simple=bytearray(0x4f8)
    struct.pack_into('<f',simple,0x54,1.0)
    struct.pack_into('<9f',simple,0x9c,1,0,0,0,1,0,0,0,1)
    struct.pack_into('<3f',simple,0x2fc,1,1,1)
    struct.pack_into('<9f',simple,0x78,1,0,0,0,1,0,0,0,1)
    direct_cases.extend((simple,force,point,normal) for force,point,normal in (
        ((-2,0,0),(1,2,0),(1,0,0)),
        ((0,-2,0),(0,0,2),(0,0,1)),
        ((1,1,0),(1,0,0),(0,1,0))))

    native_direct_cases=0
    for direct_index,(record,force,point,normal) in enumerate(direct_cases):
        cpu.mem_write(owner,bytes(record))
        for address,vector in ((force_ptr,force),(point_ptr,point),(normal_ptr,normal)):
            cpu.mem_write(address,struct.pack('<3f',*vector))
        cpu.mem_write(linear_out,bytes(12));cpu.mem_write(angular_out,bytes(12))
        oracle.call(0x00457780,(owner,force_ptr,point_ptr,normal_ptr,
                                linear_out,angular_out))
        actual=(bytes(cpu.mem_read(linear_out,12)),bytes(cpu.mem_read(angular_out,12)))
        linear,angular=contact_response(record,force,point,normal)
        expected=(struct.pack('<3f',*linear),struct.pack('<3f',*angular))
        if actual!=expected:
            raise AssertionError(f'0x457780 mismatch: original '
                                 f'{[item.hex() for item in actual]}, '
                                 f'Python {[item.hex() for item in expected]}')
        if native_runner is not None and (direct_index<3 or direct_index>=131):
            values=tuple(struct.unpack('<3f',struct.pack('<3f',*vector))
                         for vector in (force,point,normal))
            payload='0 '+bytes(record).hex()+' '+' '.join(
                format(value,'.9g') for vector in values for value in vector)+'\n'
            result=subprocess.run([str(native_runner)],input=payload,text=True,
                                  capture_output=True,check=True)
            native=bytes.fromhex(result.stdout.strip())
            if native!=b''.join(actual):
                raise AssertionError('native 0x457780 mismatch: '
                                     f'case {direct_index}: {native.hex()} != '
                                     f'{b"".join(actual).hex()}')
            native_direct_cases+=1

    original_contacts=[]
    def translated_contact(machine,address,_size,_data):
        if address != 0x00457780: return
        stack=machine.reg_read(reg.UC_X86_REG_ESP)
        values=struct.unpack('<7I',machine.mem_read(stack,28))
        ret,*words=values
        rec=bytes(machine.mem_read(words[0],0x4f8))
        vectors=[struct.unpack('<3f',machine.mem_read(ptr,12)) for ptr in words[1:4]]
        original_contacts.append(tuple(tuple(v) for v in vectors))
        try:
            linear,angular=contact_response(rec,*vectors)
        except Exception as exc:
            raise RuntimeError(f'contact bridge args={words}, vectors={vectors}, '
                               f'mass={struct.unpack_from("<f",rec,0x54)[0]}, '
                               f'matrix={struct.unpack_from("<9f",rec,0x78)}, '
                               f'inertia={struct.unpack_from("<9f",rec,0x9c)}, '
                               f'scales={struct.unpack_from("<3f",rec,0x2fc)}') from exc
        machine.mem_write(words[4],struct.pack('<3f',*linear))
        machine.mem_write(words[5],struct.pack('<3f',*angular))
        machine.reg_write(reg.UC_X86_REG_ESP,stack+4)
        machine.reg_write(reg.UC_X86_REG_EIP,ret)
    cpu.hook_add(UC_HOOK_CODE,translated_contact,
                 begin=0x00457780,end=0x00457780)

    integration_cases=0
    native_integration_cases=0
    integration_inputs=[(scale, None) for scale in (0.0,0.25,0.5,1.0)]
    integration_inputs.extend((rng.uniform(-0.5,0.5), index)
                              for index in range(32))
    for scale, random_index in integration_inputs:
        record=bytearray(0x4f8)
        record[4]=1
        record[6]=0
        struct.pack_into('<h',record,0x3bc,2)
        struct.pack_into('<3f',record,8,0,0,0)
        if random_index is None:
            velocity=(1.0,0.0,0.0)
            basis=(1,0,0,0,1,0,0,0,1)
            inertia=(1,0,0,0,1,0,0,0,1)
            mass=1.0
            scale_vector=(1,1,1)
            points=tuple((scale+1,scale,scale*.5) for _ in range(6))
            aero=(scale+1,)*4
        else:
            velocity=(rng.uniform(.25,2),rng.uniform(-.5,.5),rng.uniform(-.5,.5))
            basis=tuple(rng.uniform(-1,1) for _ in range(9))
            inertia=tuple(rng.uniform(-2,2) for _ in range(9))
            mass=rng.uniform(.25,3)
            scale_vector=tuple(rng.uniform(.25,2) for _ in range(3))
            points=tuple((rng.uniform(.25,2),rng.uniform(-1,1),rng.uniform(-1,1))
                         for _ in range(6))
            aero=tuple(rng.uniform(.1,2) for _ in range(4))
        struct.pack_into('<3f',record,0x14,*velocity)
        struct.pack_into('<9f',record,0x78,*basis)
        struct.pack_into('<f',record,0x54,mass)
        struct.pack_into('<3f',record,0x2fc,*scale_vector)
        struct.pack_into('<9f',record,0x9c,*inertia)
        for offset,point in zip((0x248,0x254,0x260,0x26c,0x278,0x284),points):
            struct.pack_into('<3f',record,offset,*point)
        for offset,value in zip((0xd0,0xcc,0xd4,0x308,0x30c,0x310,0x314),
                                (aero[0],aero[1],aero[2],aero[3],
                                 aero[0],aero[1],aero[2])):
            struct.pack_into('<f',record,offset,value)
        cpu.mem_write(owner,bytes(record))
        original_contacts.clear()
        oracle.call(0x0051FC00,(owner,))
        original=bytes(cpu.mem_read(owner,len(record)))
        translated=bytearray(record)
        translated_contacts=[]
        def capture_response(image,force,point,normal):
            translated_contacts.append(tuple(tuple(v) for v in (force,point,normal)))
            return contact_response(image,force,point,normal)
        contact_forces_step(translated,capture_response)
        if translated_contacts!=original_contacts:
            raise AssertionError(f'contact input mismatch: original={original_contacts!r}, '
                                 f'Python={translated_contacts!r}')
        if original!=translated:
            differences=[i for i,(a,b) in enumerate(zip(original,translated)) if a!=b]
            raise AssertionError(f'0x51fc00 mismatch at '
                                 f'{[hex(i) for i in differences[:16]]}; '
                                 f'original={[(hex(i),original[i:i+4].hex()) for i in differences[:16]]}; '
                                 f'Python={[(hex(i),translated[i:i+4].hex()) for i in differences[:16]]}')
        if native_runner is not None and random_index is None:
            result=subprocess.run([str(native_runner)],
                input='1 '+bytes(record).hex()+'\n',text=True,
                capture_output=True,check=True)
            native=bytes.fromhex(result.stdout.strip())
            if native!=original:
                differences=[i for i,(a,b) in enumerate(zip(original,native)) if a!=b]
                raise AssertionError(f'native 0x51fc00 mismatch at '
                                     f'{[hex(i) for i in differences[:16]]}')
            native_integration_cases+=1
        integration_cases+=1
    return len(direct_cases),integration_cases,native_direct_cases,native_integration_cases


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable',type=Path)
    parser.add_argument('--native-runner',type=Path)
    args=parser.parse_args()
    direct,integration,native_direct,native_integration=verify(args.executable,args.native_runner)
    print(f'contact response 0x457780 matches for {direct} cases; '
          f'six-point force pass 0x51fc00 matches for {integration} cases; '
          f'native matches {native_direct} helper and {native_integration} curated pass cases')


if __name__=='__main__':main()
