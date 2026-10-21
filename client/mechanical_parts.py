"""Owned/catalogue intermediates and original `0x52c2e0` tPartInfo fields."""
from dataclasses import dataclass
import struct
from client.tire_response import f32


MECHANICAL_PART_INFO_SIZE = 0x984
MECHANICAL_SLOT_BUFFER_STRIDE = 2 * MECHANICAL_PART_INFO_SIZE


def create_mechanical_slot_buffer(count, allocate, *, pool):
    """Translate the successful/failure allocation contract of original `0x52c6b0`.

    The original asks its pool allocator for ``count * 0x1308`` bytes, runs two
    short object initializers per slot, then clears the entire block. Those
    initializer writes are fully overwritten before return, so the portable
    image is exactly a zeroed block. Allocation policy and pool identity remain
    caller-owned. Zero count returns ``None`` without calling the allocator.
    """
    if type(count) is not int or not 0 <= count <= 10000:
        raise ValueError('mechanical slot count must be a bounded nonnegative integer')
    if not callable(allocate):
        raise TypeError('allocate must be callable')
    if type(pool) is not int or not 0 <= pool <= 0xffffffff:
        raise ValueError('allocator pool must be an unsigned 32-bit value')
    if count == 0:
        return None
    size = count * MECHANICAL_SLOT_BUFFER_STRIDE
    block = allocate(b'PARTS', size, pool)
    if block is None:
        return None
    if not isinstance(block, bytearray) or len(block) != size:
        raise ValueError('allocator must return a bytearray of the requested size')
    block[:] = bytes(size)
    return block


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


def transfer_mechanical_presentation(slot, *, model_prefix, initial_image):
    """Translate the string/path writes from original `0x52c2e0`.

    `model_prefix` is the runtime entry returned by `0x530a90(15)`; its
    population is outside this adapter. The operation writes only fields
    touched by the presentation region and preserves every other byte.
    """
    if not isinstance(slot, bytes) or len(slot) != 0x63c:
        raise ValueError('expected 1596-byte source intermediate')
    if not isinstance(initial_image, bytes) or len(initial_image) != 0x984:
        raise ValueError('expected 2436-byte mechanical image')
    if isinstance(model_prefix, str):
        try:
            model_prefix = model_prefix.encode('ascii')
        except UnicodeEncodeError as error:
            raise ValueError('model prefix must be ASCII') from error
    if not isinstance(model_prefix, bytes) or b'\0' in model_prefix:
        raise ValueError('model prefix must be NUL-free bytes or ASCII text')

    def c_string(start, end, label):
        value = slot[start:end]
        terminator = value.find(b'\0')
        if terminator < 0:
            raise ValueError(f'{label} requires a bounded terminator')
        return value[:terminator]

    out = bytearray(initial_image)
    key = c_string(0x387, 0x390, 'model-source key')
    if key:
        out[0x220:0x228] = key[:8].ljust(8, b'\0')
        out[0x228] = 0
        path = key if key.startswith(b'.') else model_prefix + key + b'.viv'
        if 0x22c + len(path) >= len(out):
            raise ValueError('model-source path exceeds the tPartInfo image')
        out[0x22c:0x22c + len(path) + 1] = path + b'\0'

    manufacturer = slot[0x390:0x398]
    if manufacturer and manufacturer[0] != 0:
        out[0x32c:0x334] = manufacturer
        out[0x334] = 0

    brand = c_string(0x2c7, 0x307, 'display brand')
    name = c_string(0x307, 0x387, 'display name')
    picture = (brand + b' ' + name)[:63]
    out[0x53f:0x53f + len(picture) + 1] = picture + b'\0'
    return bytes(out)


def expand_mechanical_parts(slots, *, model_prefix=None):
    """Recover `0x52c550` selection and emit its `0x52c2e0` part records.

    The original emits 5/6 for paired attachment zero, 1/2 for front (10),
    3/4 for rear (11); other attachments pass through. Missing branded parts
    are skipped. The returned source index always refers to the input slot,
    including across skipped entries. When `model_prefix` is supplied, each
    record also receives the original model-source and display strings.
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
            image=transfer_mechanical_physics(slot,selected)
            if model_prefix is not None:
                image=transfer_mechanical_presentation(
                    slot,model_prefix=model_prefix,initial_image=image)
            result.append(MechanicalPart(index,selected,image))
    return tuple(result)
