"""Plane-height calculations recovered from the world renderer."""
import struct


def plane_height(normal, reference, point):
    """Return the Y coordinate on a plane through `reference` at XZ `point`.

    This matches 0x4b71a0 over finite, nonvertical normals. Inputs contain
    three binary32 values in XYZ order.
    """
    for name,vector in (('normal',normal),('reference',reference),
                        ('point',point)):
        if (not isinstance(vector,(tuple,list)) or len(vector)!=3 or
            any(not isinstance(value,(int,float)) for value in vector)):
            raise ValueError(f'{name} must contain three numeric values')
    normal_y=float(normal[1])
    def f32(value):
        return struct.unpack('<f',struct.pack('<f',float(value)))[0]
    normal=tuple(f32(value) for value in normal)
    reference=tuple(f32(value) for value in reference)
    point=tuple(f32(value) for value in point)
    normal_y=normal[1]
    if normal_y==0:
        raise ValueError('vertical planes do not define a finite height')
    x_term=(float(point[0])-float(reference[0]))*float(normal[0])
    z_term=(float(point[2])-float(reference[2]))*float(normal[2])
    height=-((x_term+z_term)/normal_y)+float(reference[1])
    try:
        return struct.unpack('<f',struct.pack('<f',height))[0]
    except OverflowError:
        return float('-inf') if height<0 else float('inf')
