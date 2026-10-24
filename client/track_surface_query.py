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
