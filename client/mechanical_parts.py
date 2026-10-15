"""Owned/catalogue intermediate to mechanical physics input, original 0x52c2e0.

Only the physics/numeric copy is recovered here. Geometry filenames, pictures
and display formatting are separate, unexecuted passes. Records stay internal;
they are neither network packets nor mod API structures.
"""
from dataclasses import dataclass
import struct
from client.tire_response import f32


@dataclass(frozen=True)
class MechanicalPart:
    source_index: int
    attachment: int
    image: bytes


def transfer_mechanical_physics(slot,attachment,*,initial_image=None):
    """Copy verified numeric prefix and physics/text tail, preserving gaps.

    Damage/wear are converted as unsigned 32-bit integers, as in the original,
    even though their SQL loader uses signed integer storage. Numeric Physics
    slots copy all fifty stored values, independent of the count header.
    """
    if not isinstance(slot,bytes) or len(slot)!=0x63c:
        raise ValueError('expected 1596-byte source intermediate')
    if type(attachment) is not int or not -0x80000000<=attachment<=0x7fffffff:
        raise ValueError('mechanical attachment must fit int32')
    out=bytearray(0x984) if initial_image is None else bytearray(initial_image)
    if len(out)!=0x984:raise ValueError('expected 2436-byte mechanical image')
    def unsigned(offset):return struct.unpack_from('<I',slot,offset)[0]
    def put(offset,value):struct.pack_into('<f',out,offset,value)
    out[0x338:0x974]=slot
    struct.pack_into('<i',out,0x18,attachment)
    damage=f32(unsigned(0x610)*f32(.01))
    wear=f32(unsigned(0x614)*1000.)
    for offset in (0x104,0x10c,0x114):put(offset,damage)
    for offset in (0x108,0x110,0x118):put(offset,wear)
    put(0x20,struct.unpack_from('<i',slot,0x1ef)[0]*1000.)
    for destination,source in ((0x24,0x408),(0x28,0x40c),(0x2c,0x410),
                               (0x34,0x418),(0x38,0x41c)):
        put(destination,unsigned(source))
    for destination,source in ((0x30,0x414),(0xc,0x428),(0x14,0x420)):
        out[destination:destination+4]=slot[source:source+4]
    out[0x3c:0x104]=slot[0x42c:0x4f4]
    for index in range(min(unsigned(0x424),8)):
        source=0x4f4+index*32;destination=0x120+index*32
        value=slot[source:source+32]
        if b'\0' not in value:raise ValueError('physics text requires a bounded terminator')
        value=value.split(b'\0',1)[0]+b'\0'
        out[destination:destination+len(value)]=value
    return bytes(out)


def expand_mechanical_parts(slots):
    """Recover 0x52c550 source selection and paired attachments, sans pointers.

    The original emits 5/6 for paired attachment zero, 1/2 for front (10),
    3/4 for rear (11); other attachments pass through. Missing branded parts
    are skipped. The returned source index always refers to the input slot,
    including across skipped entries. Geometry/display passes remain required.
    """
    if not isinstance(slots,(tuple,list)) or len(slots)>10000:
        raise ValueError('expected at most 10000 source slots')
    result=[]
    for index,slot in enumerate(slots):
        if not isinstance(slot,bytes) or len(slot)!=1596:
            raise ValueError('expected 1596-byte source intermediate')
        if struct.unpack_from('<I',slot,0x1e3)[0]==0:continue
        attachment=struct.unpack_from('<i',slot,0x61c)[0]
        paired=struct.unpack_from('<i',slot,0x10)[0]!=0
        attachments={0:(5,6),10:(1,2),11:(3,4)}.get(attachment,(attachment,)) if paired else (attachment,)
        for selected in attachments:
            result.append(MechanicalPart(index,selected,transfer_mechanical_physics(slot,selected)))
    return tuple(result)
