"""All-inside quad dispatch recovered from the MCO renderer."""
from dataclasses import dataclass
import struct


@dataclass(frozen=True)
class QuadDispatchResult:
    vertices: tuple
    callback_words: object


def _float_from_word(word):
    return struct.unpack('<f',struct.pack('<I',word))[0]


def _float_word(value):
    try:
        return struct.unpack('<I',struct.pack('<f',value))[0]
    except OverflowError:
        return 0xff800000 if value < 0 else 0x7f800000


def dispatch_inside_quad(vertices, near_w, far_w):
    """Translate 0x474ee0's all-four-clip-codes-zero branch.

    Each vertex is eight raw dwords. Word 5's low byte is its clip code;
    words 6 and 7 remain stack residue. This branch updates word 2 to
    ``near_w - W`` for nonnegative W no farther than near, otherwise far_w.
    It dispatches all four records, including canonical-NaN inputs observed
    in direct execution. Other polygon clipping branches are separate.
    """
    if not isinstance(vertices,(tuple,list)) or len(vertices)!=4 or any(
        not isinstance(vertex,(tuple,list)) or len(vertex)!=8 or any(
            type(word) is not int or not 0<=word<=0xffffffff
            for word in vertex) for vertex in vertices):
        raise ValueError('quad dispatch requires four eight-word vertices')
    if any(vertex[5]&0xff for vertex in vertices):
        raise ValueError('all vertex clip codes must be zero')
    if any(not isinstance(value,(int,float)) for value in (near_w,far_w)):
        raise ValueError('depth limits must be numeric')
    near_w=_float_from_word(_float_word(float(near_w)))
    far_word=_float_word(float(far_w))
    output=[]
    for vertex in vertices:
        words=list(vertex)
        w=words[3]
        if not w&0x80000000 and _float_from_word(w)<=near_w:
            words[2]=_float_word(near_w-_float_from_word(w))
        else:
            words[2]=far_word
        output.append(tuple(words))
    return QuadDispatchResult(tuple(output),tuple(output))


def dispatch_first_fan_triangle(vertices, near_w, far_w):
    """Translate 0x474ee0 when only the fourth fan corner is outside.

    If vertices 0, 1, and 2 have zero clip codes, their triangle is depth
    adjusted and sent to THRASH_drawtri. Other clip-code patterns belong to
    separate clipping paths and return no event here.
    """
    _validate_quad(vertices,near_w,far_w)
    return _dispatch_fan_triangle(vertices,(0,1,2),3,near_w,far_w)


def dispatch_second_fan_triangle(vertices, near_w, far_w):
    """Translate the fan branch emitting vertices 0, 2, 3 when vertex 1 is outside."""
    _validate_quad(vertices,near_w,far_w)
    return _dispatch_fan_triangle(vertices,(0,2,3),1,near_w,far_w)


def _validate_quad(vertices,near_w,far_w):
    if not isinstance(vertices,(tuple,list)) or len(vertices)!=4 or any(
        not isinstance(vertex,(tuple,list)) or len(vertex)!=8 or any(
            type(word) is not int or not 0<=word<=0xffffffff
            for word in vertex) for vertex in vertices):
        raise ValueError('quad dispatch requires four eight-word vertices')
    if any(not isinstance(value,(int,float)) for value in (near_w,far_w)):
        raise ValueError('depth limits must be numeric')


def _dispatch_fan_triangle(vertices, triangle_indices, outside_index,
                           near_w, far_w):
    codes=tuple(vertex[5]&0xff for vertex in vertices)
    if (any(codes[index]!=0 for index in triangle_indices) or
            codes[outside_index]==0):
        return None
    near_w=_float_from_word(_float_word(float(near_w)))
    far_word=_float_word(float(far_w))
    output=[]
    for index in triangle_indices:
        vertex=vertices[index]
        words=list(vertex)
        w=words[3]
        if not w&0x80000000 and _float_from_word(w)<=near_w:
            words[2]=_float_word(near_w-_float_from_word(w))
        else:
            words[2]=far_word
        output.append(tuple(words))
    checked=(0,1,2,3,6,7)
    if any((vertex[index]|0x80000000)==0xffc00000
           for vertex in output for index in checked):
        callback=None
    else:
        callback=tuple(output)
    return QuadDispatchResult(tuple(output),callback)
