"""Endpoint construction and clipping dispatch recovered from MCO."""
from dataclasses import dataclass
import struct

from .render_clip_code import RenderClipBounds, render_clip_code
from .render_segment_clip import SegmentClipBounds, clip_render_segment


@dataclass(frozen=True)
class RenderSegmentResult:
    first_words: tuple
    second_words: tuple
    first_code: int
    second_code: int
    clipped_words: object


def _signed32(value):
    value &= 0xffffffff
    return value if value < 0x80000000 else value-(1<<32)


def _float_word(value):
    try:
        return struct.unpack('<I',struct.pack('<f',value))[0]
    except OverflowError:
        return 0xff800000 if value < 0 else 0x7f800000


def construct_render_segment(x1,y1,x2,y2,attribute1,attribute2,
                             clip_code_bounds,segment_bounds,*,opaque_words):
    """Translate native 0x482610 through its 0x6cb970 callback boundary.

    The two opaque words are the source function's untouched stack fields at
    endpoint offset +20. They are mandatory inputs because the native body
    never initializes them. Attributes are passed as raw 32-bit words.
    """
    coordinates=(x1,y1,x2,y2)
    if any(type(value) is not int or not -0x80000000<=value<=0x7fffffff
           for value in coordinates):
        raise ValueError('segment coordinates must be signed 32-bit integers')
    if any(type(value) is not int or not 0<=value<=0xffffffff
           for value in (attribute1,attribute2)):
        raise ValueError('segment attributes must be unsigned 32-bit words')
    if (not isinstance(opaque_words,(tuple,list)) or len(opaque_words)!=2 or
        any(type(value) is not int or not 0<=value<=0xffffffff
            for value in opaque_words)):
        raise ValueError('both untouched stack words must be supplied')
    if not isinstance(clip_code_bounds,RenderClipBounds):
        raise TypeError('clip_code_bounds must be RenderClipBounds')
    if not isinstance(segment_bounds,SegmentClipBounds):
        raise TypeError('segment_bounds must be SegmentClipBounds')

    first=( _float_word(x1),_float_word(y1),0x3f7fff00,0x37800080,
            attribute1,opaque_words[0])
    second=(_float_word(x2),_float_word(y2),0x3f7fff00,0x37800080,
            attribute2,opaque_words[1])
    code1=render_clip_code(tuple(_signed32(x) for x in first[:4]),
                           clip_code_bounds)
    code2=render_clip_code(tuple(_signed32(x) for x in second[:4]),
                           clip_code_bounds)

    first_xyzw=struct.unpack('<4f',struct.pack('<4I',*first[:4]))
    second_xyzw=struct.unpack('<4f',struct.pack('<4I',*second[:4]))
    clipped=clip_render_segment((*first_xyzw,0.0,0.0),
                                (*second_xyzw,0.0,0.0),
                                code1,code2,segment_bounds)
    if clipped is None:
        clipped_words=None
    else:
        clipped_words=tuple(
            tuple(_float_word(value) for value in endpoint[:4]) +
            tuple(original[4:])
            for endpoint,original in zip(clipped,(first,second)))
    return RenderSegmentResult(first,second,code1,code2,clipped_words)
