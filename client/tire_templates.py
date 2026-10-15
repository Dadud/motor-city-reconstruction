"""External GetTireAuxData records in the recovered internal table layout."""
import math
import struct
import logging

TEMPLATE_SIZE=0x1d68
TEMPLATE_STRIDE=0x178
TIRE_QUERY_COLUMNS=('TireTypeID',*(f'Val{i+1}' for i in range(36)),
    'TireType','RainFlag','Pacejka_TireModel',*(f'LatForce{i+1}' for i in range(25)),
    *(f'AlignMom{i+1}' for i in range(25)),'RollingResistFactor','GrowthFactor',
    'PeakFriction','CamberCoefficient','SectionWidth')


def build_tire_templates(rows):
    """Saved query selects Pacejka_TireModel.*, ordered by TireTypeID.

    The original reserves twenty records and clears unused slots. Header pointer
    is process-specific and unused by the consumer; the portable image uses zero.
    Raw database values remain externally supplied and are never bundled.
    """
    rows=tuple(rows)
    if len(rows)>20:raise ValueError('original tire auxiliary table permits twenty records')
    identities=[row['TireTypeID'] for row in rows]
    if any(type(v) is not int or not 0<=v<=0x7fffffff for v in identities) or len(set(identities))!=len(rows):
        raise ValueError('unique nonnegative tire template identities required')
    out=bytearray(TEMPLATE_SIZE)
    for index,row in enumerate(sorted(rows,key=lambda row:row['TireTypeID'])):
        base=4+index*TEMPLATE_STRIDE
        for offset,key in ((0,'TireTypeID'),(4,'TireType'),(8,'RainFlag')):
            value=row[key]
            if type(value) is not int or not -0x80000000<=value<=0x7fffffff:
                raise ValueError('32-bit tire template integer required')
            struct.pack_into('<i',out,base+offset,value)
        fields=[*((12+i*4,f'Val{i+1}') for i in range(36)),
            *((0x9c+i*4,f'LatForce{i+1}') for i in range(25)),
            *((0x100+i*4,f'AlignMom{i+1}') for i in range(25)),
            (0x164,'RollingResistFactor'),(0x168,'GrowthFactor'),
            (0x16c,'PeakFriction'),(0x170,'CamberCoefficient'),(0x174,'SectionWidth')]
        for offset,key in fields:
            value=row[key]
            if not isinstance(value,(int,float)) or not math.isfinite(value):
                raise ValueError('finite tire template number required')
            struct.pack_into('<f',out,base+offset,value)
    struct.pack_into('<I',out,0x1d64,len(rows))
    return bytes(out)


def read_tire_template_rows(database):
    from access_parser import AccessParser
    from client.catalogue import validated_rows
    class MetadataDiagnostics(logging.Filter):
        def filter(self,record):
            return record.getMessage()!='Error while parsing MSysObjects table chunk.'
    logger=logging.getLogger('access_parser');diagnostics=MetadataDiagnostics()
    logger.addFilter(diagnostics)
    try:table=AccessParser(str(database)).get_table('Pacejka_TireModel')
    finally:logger.removeFilter(diagnostics)
    if table is None:raise ValueError('missing Pacejka_TireModel table')
    # Parser iteration follows physical storage, which moves the variable text
    # column to the end. Jet SELECT * follows column IDs, including that column.
    columns=tuple(c.col_name_str for c in sorted(table.columns.values(),key=lambda c:c.column_id))
    if columns!=TIRE_QUERY_COLUMNS:raise ValueError('unsupported tire auxiliary query column order')
    rows=validated_rows('Pacejka_TireModel',table.parse(),table.table_header.number_of_rows,'TireTypeID')
    return tuple(sorted(rows,key=lambda row:row['TireTypeID']))


def load_tire_templates(database):
    return build_tire_templates(read_tire_template_rows(database))
