"""MCO base track block geometry from REA 0x428150 and 0x428680 assembly.

Object payload bytes and descriptors are retained but not rendered. UVs and
material references are decoded; object rendering, collision and animated
scenery remain to reconstruct.
"""
import math
import struct
from dataclasses import dataclass, replace
from .fce import Model, Part, Triangle
from .track import decode_track
from .track_spatial import (SpatialIndex, decode_relocated_spatial,
                            decode_spatial)
from .world_grid import WorldGridFixup, fixup_world_grid


@dataclass(frozen=True)
class DecodedTrackWorld:
    mesh: Model
    grid: WorldGridFixup
    spatial: SpatialIndex
    end_offset: int
    block_headers: tuple[bytes, ...] = ()
    object_sections: tuple[tuple[int, tuple[int, int, int, int]], ...] = ()
    objects: tuple['TrackObjectGroup', ...] = ()
    object_meshes: tuple[Model, ...] = ()

    def sample_object_poses(self, tick):
        """Sample the animation payload for each animated type-3 object."""
        from client.track_object_animation import evaluate_track_object_animation
        return tuple(tuple(
            evaluate_track_object_animation(obj.animation, tick)
            if obj.animation and (obj.descriptor[2] & 0xf) == 3 else None
            for obj in group.objects) for group in self.objects)


@dataclass(frozen=True)
class TrackObject:
    descriptor: bytes
    animation: bytes
    vertex_records: tuple[bytes, ...]
    vertex_attributes: tuple[bytes, ...]
    faces: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class TrackObjectGroup:
    block_index: int
    section_offset: int
    objects: tuple[TrackObject, ...]


def decode_mesh(data, materials=False, surface_records=None, object_records=None):
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
            take(animation+vertices*16+faces*30)
            if faces & 1:
                take(2)

    def decode_objects(count, block_index, section_offset):
        if count > 100000:
            raise ValueError('FRD object count exceeds budget')
        start = take(count * 56)
        decoded = []
        for index in range(count):
            record = start + index * 56
            animation_size, vertex_count, face_count = (
                count_at(record + offset) for offset in (28, 36, 48))
            if vertex_count > 2_000_000 or face_count > 2_000_000:
                raise ValueError('FRD object geometry exceeds budget')
            animation_start = take(animation_size)
            vertex_start = take(vertex_count * 16)
            position_start = vertex_start
            attribute_start = vertex_start + vertex_count * 12
            vertex_records = tuple(bytes(data[position_start + i * 12:
                                               position_start + (i + 1) * 12])
                                    for i in range(vertex_count))
            attributes = tuple(bytes(data[attribute_start + i * 4:
                                          attribute_start + (i + 1) * 4])
                               for i in range(vertex_count))
            face_start = take(face_count * 30)
            faces = tuple(struct.unpack_from('<15H', data, face_start + i * 30)
                          for i in range(face_count))
            if face_count & 1:
                take(2)
            decoded.append(TrackObject(bytes(data[record:record + 56]),
                                       bytes(data[animation_start:animation_start + animation_size]),
                                       vertex_records, attributes, faces))
        if object_records is not None and decoded:
            object_records.append(TrackObjectGroup(block_index, section_offset,
                                                   tuple(decoded)))

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
            if object_records is None:
                skip_objects(count_at(header+offset))
            else:
                decode_objects(count_at(header+offset), block, offset)
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


def decode_track_world(data, image_address=0x71000000, *, retain_block_headers=True):
    """Decode mesh, relocate the native grid trailer, and build its query view."""
    objects = []
    mesh, grid_offset = decode_mesh(data, materials=True, object_records=objects)
    uv_count = struct.unpack_from('<I', data, 52)[0] & 0xffff
    uv_start = grid_offset - uv_count * 4
    uv_coordinates = struct.unpack_from(f'<{uv_count}f', data, uv_start)
    from client.track_object_mesh import decode_track_object_group
    object_meshes = tuple(decode_track_object_group(group, uv_coordinates)
                          for group in objects)
    track = decode_track(data)
    header_start = 56 + len(track.slices) * 84
    if retain_block_headers:
        headers = tuple(bytes(data[header_start + block * 0x6c4:
                                   header_start + (block + 1) * 0x6c4])
                        for block in range(track.block_count))
        sections = tuple((block, tuple(struct.unpack_from('<I', data,
                        header_start + block * 0x6c4 + offset)[0]
                        for offset in (0x640, 0x648, 0x650, 0x658)))
                         for block in range(track.block_count))
    else:
        headers = sections = ()
    grid = fixup_world_grid(memoryview(data)[grid_offset:], image_address)
    spatial, end = decode_spatial(data, grid_offset)
    if end != len(data):
        raise ValueError('FRD world-grid trailer does not end at EOF')
    if spatial.bounds != grid.bounds:
        raise ValueError('FRD spatial and relocated-grid bounds disagree')
    relocated = decode_relocated_spatial(grid.bounds, grid.table, grid.payload,
                                         image_address)
    if relocated != spatial:
        raise ValueError('relocated and file-layout spatial trees disagree')
    return DecodedTrackWorld(mesh, grid, relocated, end, headers, sections,
                             tuple(objects), object_meshes)


def decode_track_with_spatial(data):
    """Compatibility tuple form of :func:`decode_track_world`."""
    world = decode_track_world(data)
    return world.mesh, world.spatial, world.end_offset
