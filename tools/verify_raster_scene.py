"""Compare scene-node and face traversal of 0x4836f0 with original masks."""
import argparse
import random
import struct
import subprocess
from pathlib import Path

from client.raster_scene import RasterMesh, rasterize_scene_geometry
from tools.native_oracle import DynoOracle

RASTER_BYTES = 321 * 241
MIRROR_TYPES = (5, 6, 9, 10, 13)


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


class SceneOracle:
    """Build synthetic linked nodes and model face buffers for 0x4836f0."""

    def __init__(self, executable):
        self.oracle = DynoOracle(executable)
        self.cpu = self.oracle.cpu
        self.root = self.oracle.inputs
        self.owner = self.root + 0x1000
        self.context = self.root + 0x2000
        self.node_base = self.root + 0x3000
        self.model_base = 0x74000000
        self.cpu.mem_map(self.model_base, 0x100000)
        self.bitmap = 0x73000000
        self.cpu.mem_map(self.bitmap, 0x20000)

    def u16(self, address, value):
        self.cpu.mem_write(address, struct.pack('<H', value & 0xffff))

    def u32(self, address, value):
        self.cpu.mem_write(address, struct.pack('<I', value & 0xffffffff))

    def f32(self, address, value):
        self.cpu.mem_write(address, struct.pack('<f', value))

    def populate(self, meshes):
        self.u32(self.owner + 0x490, self.context)
        head = self.node_base if meshes else 0
        self.u32(self.context + 0x21c, head)
        for ordinal, mesh in enumerate(meshes):
            node = self.node_base + ordinal * 0x100
            next_node = self.node_base + (ordinal + 1) * 0x100 if ordinal + 1 < len(meshes) else 0
            model = self.model_base + ordinal * 0x10000
            self.u32(node, next_node)
            self.u32(node + 4, model if mesh.has_model else 0)
            self.u16(node + 12, mesh.surface_id)
            self.u32(node + 20, mesh.mesh_type)
            if not mesh.has_model:
                continue
            self.cpu.mem_write(model, bytes(0x5000))
            self.u32(model + 0x14, 0x2000)
            self.u32(model + 0x1c, 0)
            self.u32(model + 0x420 + mesh.surface_id * 4, mesh.vertex_base)
            self.u32(model + 0x620 + mesh.surface_id * 4, mesh.face_base)
            self.u32(model + 0x720 + mesh.surface_id * 4, len(mesh.triangles))
            for index, (x, y, z) in enumerate(mesh.vertices):
                address = model + 0x4038 + index * 12
                self.f32(address, x)
                self.f32(address + 4, y)
                self.f32(address + 8, z)
            for index, face in enumerate(mesh.triangles):
                for corner, vertex_index in enumerate(face):
                    self.u32(model + 0x203c + (mesh.face_base + index) * 0x38 +
                             corner * 4, vertex_index)
            for axis, value in enumerate(mesh.position):
                self.f32(model + 0x120 + mesh.surface_id * 12 + axis * 4, value)

        self.cpu.mem_write(self.bitmap, bytes(RASTER_BYTES))

    def rasterize(self, meshes, bounds):
        self.populate(meshes)
        args = (self.owner, self.bitmap, *(bits(value) for value in bounds))
        self.oracle.call(0x004836f0, args, instruction_limit=5_000_000)
        return bytes(self.cpu.mem_read(self.bitmap, RASTER_BYTES))


def make_scenes():
    scenes = [
        (RasterMesh(
            vertices=((1,1,0),(9,1,0),(5,9,0),(2,2,0),(8,2,0),(5,7,0)),
            triangles=((0,1,2),(3,4,5))),
         RasterMesh(vertices=((-1,1,0),(-9,1,0),(-5,9,0)),
                    triangles=((0,1,2),),mesh_type=5),
         RasterMesh(vertices=(),triangles=(),mesh_type=16),
         RasterMesh(vertices=(),triangles=(),has_model=False)),
        tuple(RasterMesh(vertices=((-1,1,0),(-9,1,0),(-5,9,0)),
                         triangles=((0,1,2),),mesh_type=kind)
              for kind in MIRROR_TYPES),
        (RasterMesh(
            vertices=((0,0,0),(0,0,0),(0,0,0),
                      (1,1,0),(9,1,0),(5,9,0)),
            triangles=((0,1,2),),position=(1,-1,0),mesh_type=9,
            surface_id=2,vertex_base=3,face_base=1),),
        (RasterMesh(vertices=((1,1,0),(9,1,0),(5,9,0)),
                    triangles=((0,1,2),),position=(1,-1,0)),
         RasterMesh(vertices=((-2,8,0),(5,-2,0),(12,7,0)),
                    triangles=((0,1,2),),position=(-1,1,0),mesh_type=6)),
    ]
    rng = random.Random(0x4836F0)
    for _ in range(12):
        meshes = []
        for _ in range(rng.randint(1, 4)):
            vertices = tuple((rng.uniform(-4,14),rng.uniform(-4,14),
                              rng.uniform(-1,1)) for _ in range(9))
            meshes.append(RasterMesh(
                vertices=vertices,
                triangles=((0,1,2),(3,4,5),(6,7,8))[:rng.randint(1,3)],
                position=(rng.uniform(-1,1),rng.uniform(-1,1),0),
                mesh_type=rng.choice((0,1,5,6,9,10,13,15,16))))
        scenes.append(tuple(meshes))
    return scenes


def native_line(meshes, bounds):
    words = [len(meshes), *(bits(value) for value in bounds)]
    for mesh in meshes:
        words.extend((int(mesh.has_model), mesh.mesh_type & 0xffffffff,
                      mesh.surface_id, mesh.vertex_base, mesh.face_base,
                      len(mesh.vertices), len(mesh.triangles),
                      *(bits(value) for value in mesh.position)))
        words.extend(bits(value) for vertex in mesh.vertices for value in vertex)
        words.extend(index for face in mesh.triangles for index in face)
    return ' '.join(f'{word:08x}' for word in words)


def verify(executable, native_runner=None):
    oracle = SceneOracle(executable)
    bounds = (0,10,0,10)
    scenes = make_scenes()
    lines = []
    for index, meshes in enumerate(scenes):
        original = oracle.rasterize(meshes, bounds)
        expected = rasterize_scene_geometry(meshes, bounds[:2], bounds[2:])
        if original != expected:
            differing = next(i for i, pair in enumerate(zip(original, expected))
                             if pair[0] != pair[1])
            raise AssertionError(f'Python mismatch in scene {index}, pixel '
                                 f'({differing%321},{differing//321})')
        lines.append(native_line(meshes, bounds))
    if native_runner is not None:
        result = subprocess.run([str(native_runner)],input='\n'.join(lines)+'\n',
                                text=True,capture_output=True,check=True)
        masks = result.stdout.splitlines()
        if len(masks) != len(scenes):
            raise AssertionError(f'native runner returned {len(masks)} masks, '
                                 f'expected {len(scenes)}')
        for index,(mask,meshes) in enumerate(zip(masks,scenes)):
            expected = rasterize_scene_geometry(meshes,bounds[:2],bounds[2:]).hex()
            if mask != expected:
                raise AssertionError(f'native mismatch in scene {index}')
    return len(scenes)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable',type=Path)
    parser.add_argument('--native-runner',type=Path)
    args=parser.parse_args()
    count=verify(args.executable,args.native_runner)
    print(f'0x4836f0 scene masks match for {count} synthetic linked scenes')


if __name__=='__main__': main()
