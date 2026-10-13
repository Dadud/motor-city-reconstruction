"""Recovered 496-byte Physics_Select record embedded in an owned part."""
import math
import struct
import zlib


def encode_owned_physics(row, *, text_encoding):
    """Encode original header, float32 values, text slots and unfinalized CRC.

    Query bytes must use a caller-specified narrow encoding. Numeric values
    stop at the first SQL NULL; later text fields are considered independently.
    The original clears the first two header words after assigning them.
    """
    required = ('PartTypeID','Ordinal','StatusID','DutyRating','MaxItemWear','Mass',
                *(f'Val{i}' for i in range(1,51)),*(f'TextVal{i}' for i in range(1,9)))
    if any(key not in row for key in required):
        raise ValueError('incomplete original Physics_Select row')
    def integer(key):
        value = 0 if row[key] is None else row[key]
        if type(value) is not int or not -0x80000000 <= value <= 0x7fffffff:
            raise ValueError('physics integer must fit int32')
        return value
    def number(value):
        value = 0 if value is None else value
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError('physics value must be finite numeric data')
        try:
            return struct.pack('<f',value)
        except (OverflowError,struct.error) as error:
            raise ValueError('physics value must fit float32') from error
    output = bytearray(496)
    ordinal,status,duty,wear = (integer(key) for key in ('Ordinal','StatusID','DutyRating','MaxItemWear'))
    struct.pack_into('<ii',output,8,ordinal,status)
    output[16:20] = number(row['Mass'])
    struct.pack_into('<ii',output,20,duty,wear)
    count = 0
    for index in range(50):
        value = row[f'Val{index+1}']
        if value is None:
            break
        output[40+index*4:44+index*4] = number(value)
        count += 1
    text_count = 0
    for index in range(8):
        value = row[f'TextVal{index+1}']
        if value is None:
            continue
        if not isinstance(value,str) or '\0' in value:
            raise ValueError('expected unterminated physics text')
        encoded = value.encode(text_encoding)[:32]
        output[240+index*32:272+index*32] = encoded.ljust(32,b'\0')
        text_count += 1
    struct.pack_into('<II',output,28,count,text_count)
    checksum_input = (struct.pack('<iii',integer('PartTypeID'),duty,wear)+
                      output[16:20]+output[40:240])
    struct.pack_into('<I',output,36,zlib.crc32(checksum_input)^0xffffffff)
    return bytes(output)


def apply_owned_physics(slot,row, *, text_encoding):
    if not isinstance(slot,bytes) or len(slot) != 1596:
        raise ValueError('expected owned-part intermediate slot')
    if struct.unpack_from('<i',slot,0x1e7)[0] != row['PartTypeID']:
        raise ValueError('physics row does not match owned-part type')
    physics = encode_owned_physics(row,text_encoding=text_encoding)
    output = bytearray(slot)
    output[0x404:0x5f4] = physics
    output[0x1ef:0x1f3] = physics[24:28]
    return bytes(output)
