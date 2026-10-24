"""Small geometry helpers recovered from the MCO renderer."""
from dataclasses import dataclass
import math
import struct

from .tire_response import f32


@dataclass(frozen=True)
class RenderPolygonData:
    """Caller-owned data read by native 0x478610.

    Each point record contains eight binary32 values (32 bytes); the helper
    reads only X and Y. The two header values extend the X maximum/minimum.
    """
    point_records: tuple
    header_max_x: float
    header_min_x: float


def extract_render_polygon_bounds(polygon, outputs=(None,None,None,None)):
    """Translate 0x478610, including its optional output-pointer writes.

    Returns `(x_min, y_min, width, height)`. `polygon=None` represents a null
    native structure. Each output entry may be None or a writable four-byte
    bytearray; outputs are written in native order, so aliased buffers retain
    the last store just as the original pointer arguments do.
    """
    if not isinstance(outputs,(tuple,list)) or len(outputs)!=4:
        raise ValueError('render bounds require four optional output buffers')
    if any(output is not None and
           (not isinstance(output,bytearray) or len(output)<4)
           for output in outputs):
        raise ValueError('each render-bounds output must be None or a four-byte buffer')

    if polygon is None:
        result=(0.0,0.0,0.0,0.0)
    else:
        if not isinstance(polygon,RenderPolygonData):
            raise TypeError('polygon must be RenderPolygonData or None')
        if not isinstance(polygon.point_records,(tuple,list)):
            raise ValueError('point records must be a sequence')
        x_min=10000.0
        y_min=10000.0
        x_max=-10000.0
        y_max=-10000.0
        for record in polygon.point_records:
            if not isinstance(record,(tuple,list)) or len(record)!=8:
                raise ValueError('each polygon point record requires eight floats')
            x,y=(f32(value) for value in record[:2])
            if x <= x_min:
                x_min=x
            if y <= y_min:
                y_min=y
            if x_max <= x:
                x_max=x
            if y_max <= y:
                y_max=y
        header_max_x=f32(polygon.header_max_x)
        header_min_x=f32(polygon.header_min_x)
        if x_max <= header_max_x:
            x_max=header_max_x
        if header_min_x <= x_min:
            x_min=header_min_x
        if x_min == 10000.0:
            x_min=0.0
        if y_min == 10000.0:
            y_min=0.0
        if x_max == -10000.0:
            x_max=0.0
        if y_max == -10000.0:
            y_max=0.0
        result=(x_min,y_min,f32(x_max-x_min),f32(y_max-y_min))

    for output,value in zip(outputs,result):
        if output is not None:
            struct.pack_into('<f',output,0,value)
    return result
