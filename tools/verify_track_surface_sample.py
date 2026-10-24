"""Compare the 0x42e010 track-surface sampling composition with the original."""
import argparse
import struct
from pathlib import Path

from client.track_surface_lookup import TrackSurfaceMemory, TrackSurfaceWorld
from client.track_surface_sample import sample_track_surface
from tools.native_oracle import DynoOracle
from unicorn import UC_HOOK_CODE
from tools.track_surface_cases import (BASE, BLOCKS, GEOMETRY, PATH,
                                       configurations, fixture)


def verify(executable, cases=1200):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    max_height_error = 0.0
    sampled = 0
    for case_index, (mode, cached, previous, neighbors, upward, x, z, seed) in enumerate(
            configurations()):
        arena, root, initial_query = fixture(
            mode, cached, previous, neighbors, upward, x, z, seed)
        vertices = ((0, 0, 0), (16, 1, 0), (16, 3, 16), (0, -2, 16))
        for block in range(3):
            for vertex, coordinates in enumerate(vertices):
                struct.pack_into('<3f', arena,
                                 GEOMETRY - BASE + block * 0x200 + vertex * 12,
                                 *coordinates)
        grid = root + bytes(65536 - len(root))
        cpu.mem_write(BASE, bytes(arena))
        cpu.mem_write(0x00A559D8, grid)
        cpu.mem_write(0x00A55970, struct.pack('<2f', 0, 0))
        cpu.mem_write(0x00A659D8, struct.pack('<2f', 1, 1))
        for address, value in ((0x0097C408, BLOCKS), (0x0097C38C, PATH),
                               (0x00988E38, 24), (0x0097DBEC, 2)):
            cpu.mem_write(address, struct.pack('<I', value))

        query_address, point_address = BASE + 0x8000, BASE + 0x8100
        input_point = bytearray(struct.pack('<3f', x, 7.0, z))
        cpu.mem_write(query_address, bytes(initial_query))
        cpu.mem_write(point_address, bytes(input_point))
        oracle.call(0x0042E010, (query_address, point_address, 0),
                    instruction_limit=500000)
        original_result = cpu.reg_read(oracle.reg.UC_X86_REG_EAX) & 0xffffffff
        original_query = cpu.mem_read(query_address, 68)
        original_point = cpu.mem_read(point_address, 12)

        query = bytearray(initial_query)
        point = bytearray(input_point)
        world = TrackSurfaceWorld(
            TrackSurfaceMemory(grid, bytes(arena), BASE), (0.0, 0.0), (1.0, 1.0),
            BLOCKS, PATH, 2, 24)
        result = sample_track_surface(world, query, point, 0)
        expected = struct.unpack('<3f', original_point)
        actual = struct.unpack('<3f', point)
        height_error = abs(expected[1] - actual[1])
        max_height_error = max(max_height_error, height_error)
        if result:
            sampled += 1
        if (int(result) != original_result or bytes(query) != original_query or
                actual[0] != expected[0] or actual[2] != expected[2] or
                height_error > 2e-6):
            raise AssertionError(
                f'0x42e010 mismatch case={case_index} mode={mode} cached={cached} '
                f'result={result}/{original_result} point={actual}/{expected} '
                f'height_error={height_error}; query equal={bytes(query) == original_query}')
    return cases, sampled, max_height_error


def verify_row_mode_stack_seed(executable):
    """Verify successful null-descriptor row sampling with an explicit stack seed."""
    oracle=DynoOracle(executable);cpu,reg=oracle.cpu,oracle.reg
    cpu.mem_map(0,0x10000)
    nodes=bytearray(0x8000);grid=bytearray(65536)
    def word(address,value):struct.pack_into('<I',nodes,address,value&0xffffffff)
    def real(address,value):struct.pack_into('<f',nodes,address,value)
    def half(address,value):struct.pack_into('<h',nodes,address,value)
    struct.pack_into('<4I',grid,0,0xdeadbeef,1,0x200,0)
    # A zero descriptor pointer with positive flags at +0x0a makes the real
    # track lookup succeed while 0x42dc50 selects its row-copy branch.
    for offset,value in ((0,100),(2,0),(4,0),(6,0),(8,0),(10,1)):half(offset,value)
    block,geometry,path=0x1000,0x5000,0x4000
    word(block+0x3c,geometry+0x80);word(block+0x14c,geometry)
    word(block+0x67c,0);word(block+0x680,8)
    for j in range(8):word(block+0x6a4+j*4,0xffffffff)
    for offset,value in ((0x664,0),(0x66c,0),(0x670,16),(0x678,16)):
        real(block+offset,value)
    vertices=((0,0,0),(16,1,0),(16,3,16),(0,-2,16))
    for i,vertex in enumerate(vertices):
        for j,value in enumerate(vertex):real(geometry+i*12+j*4,value)
        half(geometry+0x80+i*2,i)
    for j in range(8):
        real(path+j*0x54,j*2);real(path+j*0x54+4,2);real(path+j*0x54+8,j)
    struct.pack_into('<4I',grid,0,0xdeadbeef,1,0x200,0)
    cpu.mem_write(0,bytes(nodes));cpu.mem_write(0xa559d8,bytes(grid))
    cpu.mem_write(0xa55970,struct.pack('<2f',0,0));cpu.mem_write(0xa659d8,struct.pack('<2f',1,1))
    for address,value in ((0x0097c408,block),(0x0097c38c,path),
                          (0x00988e38,8),(0x0097dbec,0)):
        cpu.mem_write(address,struct.pack('<I',value))
    world=TrackSurfaceWorld(TrackSurfaceMemory(bytes(grid),bytes(nodes),0),
                            (0.,0.),(1.,1.),block,path,0,8)
    initial=bytearray([0x6d]*68);point=bytearray(struct.pack('<3f',8.,7.,8.))
    normal=(.3,.8,-.2);py_query=bytearray(initial);py_point=bytearray(point)
    expected_return=sample_track_surface(world,py_query,py_point,0,normal_seed=normal)
    def seed_unwritten_normal(_cpu,_address,_size,_user):
        stack=_cpu.reg_read(reg.UC_X86_REG_ESP)
        _point_ptr,query_ptr,normal_ptr=struct.unpack('<III',_cpu.mem_read(stack+4,12))
        if struct.unpack('<I',_cpu.mem_read(query_ptr+12,4))[0]==0:
            _cpu.mem_write(normal_ptr,struct.pack('<3f',*normal))
    cpu.hook_add(UC_HOOK_CODE,seed_unwritten_normal,begin=0x42dc50,end=0x42dc50)
    query_address,point_address=BASE+0x8000,BASE+0x8100
    cpu.mem_write(query_address,bytes(initial));cpu.mem_write(point_address,bytes(point))
    oracle.call(0x42e010,(query_address,point_address,0),instruction_limit=100000)
    actual_return=cpu.reg_read(reg.UC_X86_REG_EAX)
    actual_query=bytes(cpu.mem_read(query_address,68));actual_point=bytes(cpu.mem_read(point_address,12))
    if (actual_return!=int(expected_return) or actual_query!=bytes(py_query) or
        actual_point!=bytes(py_point)):
        raise AssertionError(('row-mode explicit stack seed',actual_return,expected_return,
                              actual_query.hex(),bytes(py_query).hex(),
                              struct.unpack('<3f',actual_point),struct.unpack('<3f',py_point)))
    row_index=struct.unpack_from('<I',actual_query,0)[0]
    reference_row=struct.unpack('<3f',cpu.mem_read(path+row_index*0x54,12))
    return {'return_and_query':'exact','point':'exact','normal_seed':normal,
            'reference_row':reference_row,
            'scope':'complete original 0x42e010 and 0x42e760 row path; stack normal bytes supplied at the original 0x42dc50 output boundary'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=1200)
    args = parser.parse_args()
    cases, sampled, error = verify(args.executable, args.cases)
    row_mode=verify_row_mode_stack_seed(args.executable)
    print(f'0x42e010 return/query state matches {cases} original cases; '
          f'{sampled} sampled surfaces, max height error {error:.9g}; '
          f'row-mode stack seed: {row_mode}')


if __name__ == '__main__':
    main()
