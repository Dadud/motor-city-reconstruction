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
