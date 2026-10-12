"""Observed MCO FRD road slices; detailed mesh blocks remain unresolved.

0x60ba50 reads a 56-byte header and 84-byte slices. Slice vector fields are
corroborated against local records and LibOpenNFS VRoadBlock (MIT reference).
"""
from dataclasses import dataclass
import math
import struct
from .fce import Model, Part, Triangle


@dataclass(frozen=True)
class RoadSlice:
    position: tuple[float, float, float]
    normal: tuple[float, float, float]
    forward: tuple[float, float, float]
    right: tuple[float, float, float]
    left_limit: float
    right_limit: float


@dataclass(frozen=True)
class Track:
    slices: tuple[RoadSlice, ...]
    block_count: int
    remaining_bytes: int

    def corridor(self):
        vertices, normals, triangles = [], [], []
        for road in self.slices:
            for distance in (-road.left_limit, road.right_limit):
                vertices.append(tuple(p+distance*r for p,r in zip(road.position, road.right)))
                normals.append(road.normal)
        for i in range(len(self.slices)-1):
            a=i*2
            for indices in ((a,a+1,a+2), (a+1,a+3,a+2)):
                triangles.append(Triangle(indices, (0,1,0,0,1,1), 0, 0))
        return Model((Part('Road corridor', (0,0,0), tuple(vertices), tuple(normals),
                           tuple(triangles)),), 0)


def decode_track(data):
    if len(data)<56:
        raise ValueError('FRD header truncated')
    magic=struct.unpack_from('<I',data)[0]
    if magic!=0xfeeeeb19:
        raise ValueError('unsupported FRD version')
    blocks,count=struct.unpack_from('<II',data,44)
    blocks+=1
    if not 2<=count<=100000 or not 1<=blocks<=12500:
        raise ValueError('FRD slice/block count exceeds budget')
    end=56+count*84
    if end>len(data):
        raise ValueError('FRD slices extend past EOF')
    slices=[]
    for index in range(count):
        values=struct.unpack_from('<14f',data,56+84*index)
        if not all(math.isfinite(x) for x in values):
            raise ValueError('non-finite FRD road data')
        if not 0<=values[12]<=10000 or not 0<=values[13]<=10000:
            raise ValueError('invalid FRD road limits')
        for start in (3,6,9):
            length=sum(x*x for x in values[start:start+3])
            if not 0.5<=length<=1.5:
                raise ValueError('invalid FRD road basis')
        slices.append(RoadSlice(values[:3], values[3:6], values[6:9], values[9:12],
                                values[12],values[13]))
    return Track(tuple(slices),blocks,len(data)-end)
