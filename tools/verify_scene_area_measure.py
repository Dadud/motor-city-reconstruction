"""Compare decoded scene-area calculation with the original 0x483450 body."""
import argparse
import struct
import subprocess
from pathlib import Path

from unicorn import UC_HOOK_CODE

from client.fce import Model as FceModel, Part as FcePart, Triangle as FceTriangle
from client.raster_scene import RasterMesh
from client.raster_scene import RasterSceneNode
from client.scene_area_measure import scene_area_from_nodes
from tools.verify_raster_scene import SceneOracle, bits, make_scenes, native_line


class AllocatorBackedSceneOracle(SceneOracle):
    """Execute 0x483450 with only its allocator/free boundary substituted."""

    def __init__(self, executable):
        super().__init__(executable)
        self.result_address = self.root + 0xf000
        self.allocations = 0
        self.frees = 0
        self.cpu.hook_add(UC_HOOK_CODE, self._allocator_hook)

    def _allocator_hook(self, cpu, address, size, user_data):
        if address not in (0x006ee510, 0x006ee550):
            return
        esp = cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP)
        return_address = struct.unpack('<I', cpu.mem_read(esp, 4))[0]
        if address == 0x006ee510:
            self.allocations += 1
            cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX, self.bitmap)
        else:
            self.frees += 1
        cpu.reg_write(self.oracle.reg.UC_X86_REG_ESP, esp + 4)
        cpu.reg_write(self.oracle.reg.UC_X86_REG_EIP, return_address)

    def area(self, meshes, vehicle_index=0):
        self.populate(meshes)
        self.allocations = self.frees = 0
        tail = b'\xd9\x1d' + struct.pack('<I', self.result_address)  # FSTP m32
        self.oracle.call(0x00483450, (self.owner, vehicle_index), tail=tail,
                         instruction_limit=10_000_000)
        if self.allocations != 1 or self.frees != 1:
            raise AssertionError('original scene-area body did not allocate/free once')
        return struct.unpack('<I', self.cpu.mem_read(self.result_address, 4))[0]


def decoded_nodes(meshes):
    """Create decoded-FCE equivalents of the oracle's linked-node fixtures."""
    nodes = []
    for mesh in meshes:
        model = None
        if mesh.has_model and mesh.mesh_type < 16:
            if not 0 <= mesh.surface_id < 64:
                raise ValueError('scene fixture surface ID outside bounded FCE model')
            parts = [FcePart('', (0, 0, 0), (), (), ())
                     for _ in range(mesh.surface_id + 1)]
            selected_vertices = mesh.vertices[mesh.vertex_base:]
            selected = FcePart(
                '', mesh.position, selected_vertices, (),
                tuple(FceTriangle(tuple(face), (), 0, 0) for face in mesh.triangles))
            parts[mesh.surface_id] = selected
            model = FceModel(tuple(parts), 0x101014)
        nodes.append(RasterSceneNode(model, mesh.surface_id, mesh.mesh_type))
    return tuple(nodes)


def verify(executable, native_runner=None):
    oracle = AllocatorBackedSceneOracle(executable)
    scenes = make_scenes()
    scenes.extend((
        (),
        (RasterMesh(vertices=((2,1,0),(2,5,0),(2,9,0)),
                    triangles=((0,1,2),)),),
        (RasterMesh(vertices=((1,1,0),(9,1,0),(5,9,0)),
                    triangles=((0,1,2),),mesh_type=16),),
    ))
    native_input = []
    for index, meshes in enumerate(scenes):
        original = oracle.area(meshes, vehicle_index=index)
        nodes = decoded_nodes(meshes)
        expected = bits(scene_area_from_nodes(nodes))
        if original != expected:
            raise AssertionError(f'Python scene-area mismatch at scene {index}: '
                                 f'{original:08x} != {expected:08x}')
        native_input.append(native_line(meshes, (0,10,0,10)))
    baseline = oracle.area(scenes[0], vehicle_index=0)
    alternate = oracle.area(scenes[0], vehicle_index=0x7fffffff)
    if baseline != alternate:
        raise AssertionError('0x483450 result depends on its unused vehicle-index argument')
    if native_runner is not None:
        result = subprocess.run([str(native_runner)],input='\n'.join(native_input)+'\n',
                                text=True,capture_output=True,check=True)
        outputs = result.stdout.splitlines()
        if len(outputs) != len(scenes):
            raise AssertionError(f'native runner returned {len(outputs)} results; '
                                 f'expected {len(scenes)}')
        for index,(word,meshes) in enumerate(zip(outputs,scenes)):
            expected = bits(scene_area_from_nodes(decoded_nodes(meshes)))
            if int(word,16) != expected:
                raise AssertionError(f'native scene-area mismatch at scene {index}: '
                                     f'{word} != {expected:08x}')
    return len(scenes)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable',type=Path)
    parser.add_argument('--native-runner',type=Path)
    args=parser.parse_args()
    count=verify(args.executable,args.native_runner)
    print(f'0x483450 area results match for {count} synthetic scenes '
          '(allocator/free calls intercepted)')


if __name__=='__main__': main()
