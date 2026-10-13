"""Recovered AbstractPartType query templates, external database data only."""
import math
import struct


_SPECIAL_TYPES = frozenset((101,1001,2001,3001,36001,210001,37001,4001,38001,15001,5001,6001))


def encode_part_type_template(row, *, text_encoding, parent_index=-1, depends_index=-1):
    """Encode the confirmed 1596-byte cache record, including resolved indices."""
    def integer(key):
        value = 0 if row[key] is None else row[key]
        if type(value) is not int or not -0x80000000 <= value <= 0x7fffffff:
            raise ValueError('part-type integer must fit int32')
        return value
    output = bytearray(1596)
    for offset,key in ((0,'AbstractPartTypeID'),(4,'ParentAbstractPartTypeID'),
            (8,'DependsOn'),(0x10,'PartPaired'),(0x14,'BlockFamilyCompatibility'),
            (0x18,'GarageCategory'),(0x1c,'ModifiedRule')):
        struct.pack_into('<i',output,offset,integer(key))
    struct.pack_into('<I',output,0xc,int(integer('AbstractPartTypeID') in _SPECIAL_TYPES))
    for offset,key in ((0x1db,'RepairCostModifier'),(0x1df,'ScrapValueModifier')):
        value = 0 if row[key] is None else row[key]
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError('part-type modifier must be finite numeric data')
        try:
            struct.pack_into('<f',output,offset,value)
        except (OverflowError,struct.error) as error:
            raise ValueError('part-type modifier must fit float32') from error
    for offset,count,key in ((0x180,63,'EAPT'),(0x1c0,8,'PartFilename'),
            (0x1c9,8,'SchematicPicname1'),(0x1d2,8,'SchematicPicname2'),(0x20,351,'EUT')):
        value = '' if row[key] is None else row[key]
        if not isinstance(value,str) or '\0' in value:
            raise ValueError('expected unterminated part-type text')
        output[offset:offset+count] = value.encode(text_encoding)[:count].ljust(count,b'\0')
    for offset,value in ((0x600,parent_index),(0x604,depends_index)):
        if type(value) is not int or not -1 <= value <= 0x7fffffff:
            raise ValueError('invalid resolved part-type cache index')
        struct.pack_into('<i',output,offset,value)
    return bytes(output)


def apply_part_type_template(slot,template):
    """Apply recovered helper values and copies, before display-name formatting."""
    if any(not isinstance(value,bytes) or len(value)!=1596 for value in (slot,template)):
        raise ValueError('expected part and template intermediate slots')
    if slot[:4] != template[:4]:
        raise ValueError('abstract type does not match template')
    output = bytearray(slot)
    for offset in (0xc,0x10,0x18,0x1c):
        output[offset:offset+4] = template[offset:offset+4]
    output[0x1db:0x1e3] = template[0x1db:0x1e3]
    for offset in (0x1c0,0x1c9,0x1d2):
        value = template[offset:offset+9].split(b'\0',1)[0]+b'\0'
        output[offset:offset+len(value)] = value
    return bytes(output)
