"""MCO track geometry and world data from native track-loader evidence."""
import math
import struct
from dataclasses import dataclass, replace
from .collision_palette import adjust_color_words
from .fce import Model, Part, Triangle
from .track import decode_track
from .track_spatial import (SpatialIndex, decode_relocated_spatial,
                            decode_spatial)
from .world_grid import (PAYLOAD_OFFSET, WorldGridFixup, fixup_world_grid)
from .track_surface_lookup import TrackSurfaceMemory, TrackSurfaceWorld
from .track_checksum import track_checksum
from .world_dataset_layout import layout_pointer_record_section


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
    query_world: TrackSurfaceWorld | None = None
    surface_blocks: tuple = ()
    loader_checksum: int = 0

    def sample_object_poses(self, tick):
        """Sample the animation payload for each animated type-3 object."""
        from client.track_object_animation import evaluate_track_object_animation
        return tuple(tuple(
            evaluate_track_object_animation(obj.animation, tick)
            if obj.animation and (obj.descriptor[2] & 0xf) == 3 else None
            for obj in group.objects) for group in self.objects)

    def object_meshes_at_quality(self, quality, *, include_animated=True,
                                 animation_tick=None):
        """Filter scenery by native detail and optionally pose type-3 objects."""
        if animation_tick is not None and (type(animation_tick) is not int
                                           or animation_tick < 0):
            raise ValueError('animation tick must be a nonnegative integer')
        if len(self.objects) != len(self.object_meshes):
            raise ValueError('track object records and meshes are misaligned')
        result = []
        for group, model in zip(self.objects, self.object_meshes):
            if len(group.objects) != len(model.parts):
                raise ValueError('track object group and mesh parts are misaligned')
            parts = []
            for obj, part in zip(group.objects, model.parts):
                animated = (obj.descriptor[2] & 0xf) == 3
                if ((animated and not include_animated)
                        or not part.visible_at_native_quality(quality)):
                    continue
                if animated and animation_tick is not None:
                    if not obj.animation:
                        continue
                    from client.track_object_animation import (
                        apply_track_object_pose, evaluate_track_object_animation)
                    pose = evaluate_track_object_animation(obj.animation,
                                                           animation_tick)
                    if pose is None:
                        continue
                    part = apply_track_object_pose(part, pose)
                parts.append(part)
            parts = tuple(parts)
            result.append(Model(parts, model.version, model.warnings))
        return tuple(result)


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


def decode_mesh(data, materials=False, surface_records=None, object_records=None,
                color_percentages=(100, 100, 100), runtime_layout=None):
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
        if runtime_layout is not None:
            runtime_layout['object_sections'].append((header + section_offset, start))
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
        if runtime_layout is not None:
            runtime_layout['object_sections'][-1] = (
                header + section_offset, start, cursor)
        if object_records is not None and decoded:
            object_records.append(TrackObjectGroup(block_index, section_offset,
                                                   tuple(decoded)))

    parts=[]
    for block in range(track.block_count):
        header=headers+block*0x6c4
        groups=struct.unpack_from('<11I',data,header)
        count=count_at(header+0x134)
        block_layout = {'header': header, 'vertices': None, 'colors': None,
                        'descriptors': {}, 'faces': []}
        if runtime_layout is not None:
            runtime_layout['blocks'].append(block_layout)
        total_vertices+=count
        total_faces+=sum(groups)
        if total_vertices>2_000_000 or total_faces>2_000_000:
            raise ValueError('FRD geometry exceeds budget')
        start=take(count*12)
        block_layout['vertices'] = start
        vertices=tuple(struct.unpack_from('<3f',data,start+i*12) for i in range(count))
        if not all(math.isfinite(x) for v in vertices for x in v):
            raise ValueError('non-finite FRD mesh position')
        color_start = take(count * 4)
        block_layout['colors'] = color_start
        color_bytes = bytearray(data[color_start:color_start + count * 4])
        adjust_color_words(color_bytes, count, color_percentages)
        vertex_colors = struct.unpack('<' + 'I' * count, color_bytes)
        descriptors=()
        for offset,stride in ((0x660,20),(0x684,20),(0x68c,20),(0x694,16),(0x69c,24)):
            entries=count_at(header+offset)
            start=take(entries*stride)
            block_layout['descriptors'][offset] = start
            if offset == 0x660 and surface_records is not None:
                descriptors=tuple(struct.unpack_from('<10h',data,start+i*20) for i in range(entries))
        triangles=[]
        surface_quads=[]
        sums=[[0.,0.,0.] for _ in vertices]
        for group,faces in enumerate(groups):
            start=take(faces*30)
            block_layout['faces'].append(start if faces else None)
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
                              tuple(tuple(n) for n in sums),tuple(triangles),
                              vertex_colors))
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
    if runtime_layout is not None:
        runtime_layout['grid_offset'] = cursor
    return Model(tuple(parts),0),cursor


def decode_track_world(data, image_address=0x71000000, *, retain_block_headers=True,
                       object_color_percentages=None, lighting_file=None):
    """Decode mesh, relocate the native grid trailer, and build its query view."""
    if object_color_percentages is not None and lighting_file is not None:
        raise ValueError('supply object color percentages or a lighting INI, not both')
    if lighting_file is not None:
        from client.track_lighting import read_object_color_percentages
        object_color_percentages = read_object_color_percentages(lighting_file)
    if object_color_percentages is None:
        object_color_percentages = (100, 100, 100)
    objects = []
    surface_blocks = []
    runtime_layout = {'blocks': [], 'object_sections': []}
    mesh, grid_offset = decode_mesh(data, materials=True, surface_records=surface_blocks,
                                    object_records=objects,
                                    color_percentages=object_color_percentages,
                                    runtime_layout=runtime_layout)
    runtime_layout.setdefault('grid_offset', grid_offset)
    uv_count = struct.unpack_from('<I', data, 52)[0] & 0xffff
    uv_start = grid_offset - uv_count * 4
    uv_coordinates = struct.unpack_from(f'<{uv_count}f', data, uv_start)
    from client.track_object_mesh import decode_track_object_group
    object_meshes = tuple(decode_track_object_group(
                              group, uv_coordinates,
                              color_percentages=object_color_percentages)
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
    def validate_surface_ids(node):
        if node.identifiers is not None:
            for identifier in node.identifiers:
                block, descriptor = identifier & 0xffff, identifier >> 16
                if block >= len(surface_blocks) or descriptor >= len(surface_blocks[block][2]):
                    raise ValueError('FRD spatial surface reference outside block')
        else:
            for child in node.children:
                if child is not None:
                    validate_surface_ids(child)
    for cell in spatial.cells:
        validate_surface_ids(cell)
    query_world = _build_track_surface_world(data, track, runtime_layout,
                                             image_address)
    return DecodedTrackWorld(mesh, grid, relocated, end, headers, sections,
                             tuple(objects), object_meshes, query_world,
                             tuple(surface_blocks), track_checksum(data))


def _build_track_surface_world(data, track, runtime_layout, image_address):
    """Recreate the bounded pointers written by the native FRD loader.

    The geometry arrays follow the copied block headers in the source stream;
    0x428150 lays them out in that same order. Only the query-relevant pointers
    and object record tables are fixed up here. The source file remains intact.
    """
    grid_offset = runtime_layout['grid_offset']
    if grid_offset < 56 + len(track.slices) * 84:
        raise ValueError('native FRD cursor precedes track blocks')
    image = bytearray(data[:grid_offset])
    descriptors = ((0x660, 0x67c), (0x684, 0x688), (0x68c, 0x690),
                   (0x694, 0x698), (0x69c, 0x6a0))
    for block in runtime_layout['blocks']:
        header = block['header']
        for header_offset, pointer_offset in ((0x14c, 'vertices'),
                                               (0x150, 'colors')):
            struct.pack_into('<I', image, header + header_offset,
                             0 if block[pointer_offset] is None else
                             image_address + block[pointer_offset])
        for count_offset, pointer_offset in descriptors:
            struct.pack_into('<I', image, header + pointer_offset,
                             image_address + block['descriptors'][count_offset])
        for index, face_start in enumerate(block['faces']):
            struct.pack_into('<I', image, header + 0x2c + index * 4,
                             0 if face_start is None else image_address + face_start)
    layout_ends = {}
    for descriptor_offset, record_start, expected_end in runtime_layout['object_sections']:
        descriptor_address = image_address + descriptor_offset
        result = layout_pointer_record_section(
            image, image_address, descriptor_address,
            image_address + record_start)
        layout_ends[descriptor_offset] = result['cursor_address'] - image_address
        if layout_ends[descriptor_offset] != expected_end:
            raise ValueError('native object pointer layout disagrees with the FRD stream')
    if any(offset < 0 or offset > grid_offset for offset in layout_ends.values()):
        raise ValueError('native object record pointers exceed the geometry region')

    grid_offset = runtime_layout['grid_offset']
    query_grid = fixup_world_grid(memoryview(data)[grid_offset:],
                                  image_address + grid_offset)
    nodes = bytes(image) + bytes(PAYLOAD_OFFSET) + query_grid.payload
    memory = TrackSurfaceMemory(query_grid.table, nodes, image_address)
    return TrackSurfaceWorld(memory,
        (query_grid.bounds[0], query_grid.bounds[1]),
        (query_grid.scale_x, query_grid.scale_y),
        image_address + 56 + len(track.slices) * 84,
        image_address + 56, track.block_count - 1, len(track.slices))


def decode_track_with_spatial(data):
    """Compatibility tuple form of :func:`decode_track_world`."""
    world = decode_track_world(data)
    return world.mesh, world.spatial, world.end_offset
