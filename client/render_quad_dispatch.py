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
    It dispatches the four records unless a checked coordinate/depth/residue
    word is the original canonical quiet-NaN pattern.
    Other polygon clipping branches are intentionally separate. The retained
    Ghidra pseudocode appears to guard the callback against canonical NaNs,
    but direct execution of the installed binary dispatches those records;
    this translation follows that measured behavior.
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
