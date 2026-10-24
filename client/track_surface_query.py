"""Bounded cache-query branches of the native track surface finder."""
import struct


def cached_quad_hit(point, quad):
    """Test the 0x42e760 cached XZ quad and return its integer hit position."""
    if (not isinstance(point,(tuple,list)) or len(point)!=3 or
        not isinstance(quad,(tuple,list)) or len(quad)!=4 or
        any(not isinstance(vertex,(tuple,list)) or len(vertex)!=3
            for vertex in quad)):
        raise ValueError('cached-quad test requires one XYZ point and four XYZ vertices')
    point=tuple(struct.unpack('<f',struct.pack('<f',float(v)))[0]
                for v in point)
    quad=tuple(tuple(struct.unpack('<f',struct.pack('<f',float(v)))[0]
                     for v in vertex) for vertex in quad)
    x,z=point[0],point[2]
    for a,b in zip(quad,quad[1:]+quad[:1]):
        if (a[0]-b[0])*(z-b[2]) > (a[2]-b[2])*(x-b[0]):
            return None
    return point


def nearest_track_neighbor(point, track_rows, track_index):
    """Select the nearest of track index and its +/-4 wrapped neighbors."""
    if (not isinstance(track_rows,(tuple,list)) or len(track_rows)<=8 or
        any(not isinstance(row,(bytes,bytearray)) or len(row)!=0x54
            for row in track_rows)):
        raise ValueError('neighbor search requires more than eight 0x54-byte track rows')
    count=len(track_rows)
    if type(track_index) is not int or not 0<=track_index<count:
        raise ValueError('track index is outside the supplied rows')
    if not isinstance(point,(tuple,list)) or len(point)!=3:
        raise ValueError('neighbor query must contain XYZ')
    point=tuple(struct.unpack('<f',struct.pack('<f',float(value)))[0]
                for value in point)
    forward=track_index+4
    if count<=forward:
        forward=track_index-count+4
    backward=track_index-4
    if backward<0:
        backward=count-4+track_index

    def distance(index):
        x=struct.unpack_from('<f',track_rows[index],0)[0]
        z=struct.unpack_from('<f',track_rows[index],8)[0]
        dx=struct.unpack('<f',struct.pack('<f',point[0]-x))[0]
        dz=struct.unpack('<f',struct.pack('<f',point[2]-z))[0]
        return struct.unpack('<f',struct.pack('<f',dx*dx+dz*dz))[0]

    best_index=track_index
    best_distance=distance(track_index)
    forward_distance=distance(forward)
    if forward_distance<best_distance:
        best_index=forward
        best_distance=forward_distance
    backward_distance=distance(backward)
    return best_index if best_distance<=backward_distance else backward


def nearest_track_quarter_point(point, track_rows):
    """Find the nearest XZ track row among indices 0, 4, 8, ... ."""
    if (not isinstance(track_rows,(tuple,list)) or not track_rows or
        any(not isinstance(row,(bytes,bytearray)) or len(row)!=0x54
            for row in track_rows)):
        raise ValueError('track scan requires nonempty 0x54-byte rows')
    if not isinstance(point,(tuple,list)) or len(point)!=3:
        raise ValueError('track query must contain XYZ')
    point=tuple(struct.unpack('<f',struct.pack('<f',float(value)))[0]
                for value in point)
    def f32(value):
        return struct.unpack('<f',struct.pack('<f',value))[0]
    best=0
    def distance(index):
        x=struct.unpack_from('<f',track_rows[index],0)[0]
        z=struct.unpack_from('<f',track_rows[index],8)[0]
        dx=f32(point[0]-x); dz=f32(point[2]-z)
        return f32(dx*dx+dz*dz)
    best_distance=distance(0)
    for index in range(4,len(track_rows),4):
        candidate=distance(index)
        if candidate<best_distance:
            best=index
            best_distance=candidate
    return best


def nearest_track_initialization_point(point, track_rows):
    """Select the 0,4,8,... sample with 0x42d5b0's x87 comparison order.

    The initial squared distance is stored as binary32. Later candidate sums
    remain extended until compared against that stored value, so exact XZ ties
    can update the index when the initial float rounded upward.
    """
    if (not isinstance(track_rows, (tuple, list)) or not track_rows or
            any(not isinstance(row, (bytes, bytearray)) or len(row) != 0x54
                for row in track_rows)):
        raise ValueError('track scan requires nonempty 0x54-byte rows')
    if not isinstance(point, (tuple, list)) or len(point) != 3:
        raise ValueError('track query must contain XYZ')
    point = tuple(struct.unpack('<f', struct.pack('<f', float(value)))[0]
                  for value in point)

    def distance(index):
        x = struct.unpack_from('<f', track_rows[index], 0)[0]
        z = struct.unpack_from('<f', track_rows[index], 8)[0]
        dx, dz = point[0] - x, point[2] - z
        return dx * dx + dz * dz

    def f32(value):
        return struct.unpack('<f', struct.pack('<f', value))[0]

    best = 0
    best_distance = f32(distance(0))
    for index in range(4, len(track_rows), 4):
        candidate = distance(index)
        if candidate < best_distance:
            best = index
            best_distance = f32(candidate)
    return best


def nearest_track_point(point, track_rows):
    """Find the nearest XZ track row among every row in the track table."""
    if (not isinstance(track_rows,(tuple,list)) or not track_rows or
        any(not isinstance(row,(bytes,bytearray)) or len(row)!=0x54
            for row in track_rows)):
        raise ValueError('track scan requires nonempty 0x54-byte rows')
    if not isinstance(point,(tuple,list)) or len(point)!=3:
        raise ValueError('track query must contain XYZ')
    point=tuple(struct.unpack('<f',struct.pack('<f',float(value)))[0]
                for value in point)
    def f32(value): return struct.unpack('<f',struct.pack('<f',value))[0]
    def distance(index):
        x=struct.unpack_from('<f',track_rows[index],0)[0]
        z=struct.unpack_from('<f',track_rows[index],8)[0]
        dx=f32(point[0]-x); dz=f32(point[2]-z)
        return f32(dx*dx+dz*dz)
    best=0
    best_distance=distance(0)
    for index in range(1,len(track_rows)):
        candidate=distance(index)
        if candidate<best_distance:
            best=index
            best_distance=candidate
    return best
