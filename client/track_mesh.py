"""MCO base track block geometry from REA 0x428150 and 0x428680 assembly.

Object payloads are traversed but not rendered. UVs and material references are
decoded; object rendering, collision and animated scenery remain to reconstruct.
"""
import math
import struct
from .fce import Model, Part, Triangle
from dataclasses import replace
from .track import decode_track


def decode_mesh(data, materials=False, surface_records=None):
    track = decode_track(data)
    headers = 56+len(track.slices)*84
    cursor = headers+track.block_count*0x6c4
    if cursor>len(data):
        raise ValueError('FRD block headers extend past EOF')
    total_vertices=0
    total_faces=0

    def take(size):
        nonlocal cursor
        if size<0 or cursor+size>len(data):
            raise ValueError('FRD block payload extends past EOF')
        start=cursor
        cursor+=size
        return start

    def count_at(offset):
        return struct.unpack_from('<I',data,offset)[0]

    def skip_objects(count):
        if count>100000:
            raise ValueError('FRD object count exceeds budget')
        start=take(count*56)
        for i in range(count):
            record=start+i*56
            animation,vertices,faces=(count_at(record+x) for x in (28,36,48))
            take(animation+vertices*16+faces*30+(faces & 1)*2)

    parts=[]
    for block in range(track.block_count):
        header=headers+block*0x6c4
        groups=struct.unpack_from('<11I',data,header)
        count=count_at(header+0x134)
        total_vertices+=count
        total_faces+=sum(groups)
        if total_vertices>2_000_000 or total_faces>2_000_000:
            raise ValueError('FRD geometry exceeds budget')
        start=take(count*12)
        vertices=tuple(struct.unpack_from('<3f',data,start+i*12) for i in range(count))
        if not all(math.isfinite(x) for v in vertices for x in v):
            raise ValueError('non-finite FRD mesh position')
        take(count*4)  # Vertex shading values; not interpreted yet.
        descriptors=()
        for offset,stride in ((0x660,20),(0x684,20),(0x68c,20),(0x694,16),(0x69c,24)):
            entries=count_at(header+offset)
            start=take(entries*stride)
            if offset == 0x660 and surface_records is not None:
                descriptors=tuple(struct.unpack_from('<10h',data,start+i*20) for i in range(entries))
        triangles=[]
        surface_quads=[]
        sums=[[0.,0.,0.] for _ in vertices]
        for group,faces in enumerate(groups):
            start=take(faces*30)
            for i in range(faces):
                record=struct.unpack_from('<15H',data,start+i*30)
                indices=record[:4]
                if any(index>=count for index in indices):
                    raise ValueError('FRD polygon index outside block')
                if group == 4 and surface_records is not None:
                    surface_quads.append(indices)
                # Groups 0..3 are lower-detail duplicates. Retain high-detail
                # track, miscellaneous geometry, lanes and attached mesh groups.
                if group<4:
                    continue
                for corners in ((0,1,2),(0,2,3)):
                    tri=tuple(indices[c] for c in corners)
                    if len(set(tri))<3:
                        continue
                    a,b,c=(vertices[index] for index in tri)
                    u=tuple(b[j]-a[j] for j in range(3));v=tuple(c[j]-a[j] for j in range(3))
                    normal=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
                    for index in tri:
                        for j in range(3):sums[index][j]+=normal[j]
                    # Native descriptor vertex order is 1,0,3,2, with UV pairs
                    # in that same order (0x42a560).
                    uv_corners=tuple((1,0,3,2)[c] for c in corners)
                    uv=tuple(record[4+2*c] for c in uv_corners)+tuple(record[5+2*c] for c in uv_corners)
                    triangles.append(Triangle(tri,uv if materials else (0,1,0,0,1,1),
                                              record[13] if materials else 0,record[14]))
        take((sum(groups) & 1)*2)
        for offset in (0x640,0x648,0x650,0x658):
            skip_objects(count_at(header+offset))
        if surface_records is not None:
            if any((descriptor[3] & 0xffff) >= len(surface_quads) for descriptor in descriptors):
                raise ValueError('FRD surface descriptor polygon index outside block')
            surface_records.append((vertices,tuple(surface_quads),descriptors))
        if triangles:
            parts.append(Part(f'Track block {block}',(0,0,0),vertices,
                              tuple(tuple(n) for n in sums),tuple(triangles)))
    if materials:
        for _ in range(2):
            count=count_at(take(4))
            skip_objects(count)
        count=count_at(52) & 0xffff
        start=take(count*4)
        coordinates=struct.unpack_from(f'<{count}f',data,start)
        if not all(math.isfinite(v) for v in coordinates):
            raise ValueError('non-finite FRD UV table')
        resolved=[]
        for part in parts:
            triangles=[]
            for face in part.triangles:
                if any(index>=count for index in face.uv):
                    raise ValueError('FRD UV index outside table')
                triangles.append(replace(face,uv=tuple(coordinates[index] for index in face.uv)))
            resolved.append(replace(part,triangles=tuple(triangles)))
        parts=resolved
    return Model(tuple(parts),0),cursor
