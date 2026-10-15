"""Recovered 0x54e720 assembly order and complete supported numeric path.

Unknown present dispatcher families fail explicitly. Geometry, owner startup and
special engine modes remain separate; success here is mechanical assembly only.
"""
from dataclasses import dataclass
import struct
from client.assembly_finalization import finalize_loaded_configuration
from client.engine_curve import finalize_engine_configuration
from client.mechanical_loaders import MECHANICAL_LOADERS
from client.tire_response import f32


# (abstract type, attachment or wildcard zero, minimum, maximum, requires mass).
# Authored transcription of observed dispatch semantics, not binary table bytes.
DISPATCH=(
    (20001,0,1,1,True),
    (160001,0,1,1,True),
    (1000001,0,1,1,True),
    (1100001,0,1,1,True),
    (180001,0,1,1,True),
    (190001,0,1,1,True),
    (140001,0,1,1,True),
    (130001,0,1,1,True),
    (10001,1,1,1,True),
    (10001,2,1,1,True),
    (10001,3,1,1,True),
    (10001,4,1,1,True),
    (12001,1,1,1,True),
    (12001,2,1,1,True),
    (12001,3,1,1,True),
    (12001,4,1,1,True),
    (11001,1,1,1,True),
    (11001,2,1,1,True),
    (11001,3,1,1,True),
    (11001,4,1,1,True),
    (13001,10,0,1,True),
    (13001,11,0,1,True),
    (14001,10,0,1,True),
    (14001,11,0,1,True),
    (360001,0,0,1,True),
    (350001,0,0,1,True),
    (340001,0,0,1,True),
    (340333,0,0,1,True),
    (320001,0,1,1,True),
    (330001,0,1,1,True),
    (29001,0,0,1,True),
    (30001,0,0,1,True),
    (200001,0,1,1,True),
    (1200001,0,1,1,True),
    (150001,0,0,1,True),
    (280001,0,1,1,True),
    (290001,0,1,1,True),
    (300001,0,0,1,True),
    (310001,0,0,1,True),
    (230001,0,1,1,True),
    (240001,0,1,1,True),
    (250001,0,1,1,True),
    (17001,0,0,1,False),
    (19001,0,0,1,True),
    (21001,0,0,1,True),
    (23001,0,0,1,True),
    (26001,0,0,1,True),
    (27001,0,0,1,True),
    (28001,0,0,1,True),
    (32001,0,0,1,True),
    (35001,0,0,1,True),
    (16001,0,0,1,True),
    (18001,0,0,1,True),
    (31001,0,0,1,True),
    (22001,0,0,1,True),
    (40001,0,0,1,True),
    (34001,0,0,2,True),
    (100001,1,1,1,True),
    (100001,2,1,1,True),
    (100001,4,1,1,True),
    (100001,3,1,1,True),
    (110001,1,1,1,True),
    (110001,2,1,1,True),
    (110001,4,1,1,True),
    (110001,3,1,1,True),
    (120001,1,0,1,True),
    (120001,2,0,1,True),
    (120001,4,0,1,True),
    (120001,3,0,1,True),
    (33001,0,0,1,True),
)


@dataclass(frozen=True)
class AssemblyResult:
    status: int
    configuration: bytes
    components: tuple
    loader_calls: tuple
    missing: tuple=()
    unsupported: tuple=()


def _word(part,offset):return struct.unpack_from('<I',part,offset)[0]


def stock_mechanical_components(catalogue,vehicle_id,*,percent_damage,item_wear):
    """Read stock catalogue physics with explicit authored wear/instance state."""
    from client.mechanical_parts import expand_mechanical_parts
    from client.owned_parts import OwnedPart
    slots=[]
    for index,part in enumerate(catalogue.vehicle(vehicle_id).parts):
        instance=OwnedPart(index+1,part.branded_id,percent_damage,item_wear,0,0,0)
        slot=bytearray(catalogue.owned_part_intermediate(instance,text_encoding='cp1252'))
        struct.pack_into('<i',slot,0x61c,part.attachment_id);slots.append(bytes(slot))
    return expand_mechanical_parts(slots)


def assemble_stock_vehicle(catalogue,vehicle_id,templates,*,tire_templates,percent_damage,item_wear):
    parts=stock_mechanical_components(catalogue,vehicle_id,percent_damage=percent_damage,item_wear=item_wear)
    return assemble_mechanical_components(tuple(p.image for p in parts),templates,tire_templates=tire_templates)


def assembly_report(result):
    """Stable inspection values, with no binary image or assumed model extents."""
    from dataclasses import asdict
    from client.gear_binding import bind_finalized_gear_tables
    from client.owner_binding import bind_axle_levers
    out=dict(mechanical_assembly_complete=result.status==1,missing=result.missing,
        unsupported=result.unsupported,loader_calls=result.loader_calls,
        ready_for_recovered_driving=False)
    if result.status!=1:return out
    image=result.configuration
    n=lambda offset:struct.unpack_from('<f',image,offset)[0]
    i=lambda offset:struct.unpack_from('<i',image,offset)[0]
    out.update(total_mass=n(0x20),unsprung_accumulator=n(0x28),
        assembled_front_weight_fraction=n(0x3c),wheelbase=n(0x2c),
        axle_levers=asdict(bind_axle_levers(n(0x2c),n(0x3c))),
        idle_rpm=i(0x6c),maximum_rpm=i(0x70),
        torque_curve=[dict(rpm=k*500,torque=t) for k,t in enumerate(struct.unpack_from('<25f',image,0x80))],
        gear_tables=asdict(bind_finalized_gear_tables(image,assembly_finalized=True)),
        component_quality=[struct.unpack_from('<f',p,0x1c)[0] for p in result.components])
    return out


def assemble_mechanical_components(components,templates,*,tire_templates,initial_configuration=None):
    """Run original preflight, zeroing, selection, quality and numeric finalizers.

    Return native status and partial writes after ordinary validation failures.
    Unsupported present loaders are reported without claiming assembly success.
    Safe bounded images replace native linked-list pointers.
    """
    parts=[bytes(p) for p in components]
    if len(parts)>10000 or any(len(p)!=0x984 for p in parts):
        raise ValueError('bounded complete mechanical component images required')
    initial=bytes(0x820) if initial_configuration is None else bytes(initial_configuration)
    if len(initial)!=0x820:raise ValueError('expected mechanical configuration image')
    def matches(part,kind,attachment):
        return _word(part,0x338)==kind and (attachment==0 or _word(part,0x18)==attachment)
    missing=[];unsupported=set()
    for kind,attachment,minimum,maximum,mass_required in DISPATCH:
        count=sum(matches(p,kind,attachment) for p in parts)
        if mass_required and min(count,maximum)<minimum:missing.append((kind,attachment,minimum-count))
        if count and kind not in MECHANICAL_LOADERS:unsupported.add(kind)
    if missing or unsupported:return AssemblyResult(0,initial,tuple(parts),(),tuple(missing),tuple(sorted(unsupported)))
    image=bytes(0x820);calls=[];valid=True
    for kind,attachment,minimum,maximum,mass_required in DISPATCH:
        remaining=maximum
        for index,part in enumerate(parts):
            if remaining==0:break
            if not matches(part,kind,attachment):continue
            updated=bytearray(part);struct.pack_into('<f',updated,0x1c,1.);parts[index]=bytes(updated)
            if mass_required and struct.unpack_from('<f',part,0x30)[0]==0:
                valid=False;calls.append((kind,index,'zero_mass'));continue
            result=(MECHANICAL_LOADERS[kind](image,parts[index],tire_templates)
                if kind==110001 else MECHANICAL_LOADERS[kind](image,parts[index]))
            image=result.configuration;parts[index]=result.component;calls.append((kind,index,result.status))
            if result.status:valid=False
            else:remaining-=1
    if not valid:return AssemblyResult(0,image,tuple(parts),tuple(calls))
    # 0x54e5e0 only searches and returns presence; callers discard its result.
    # 0x54eaa0 modifies only the first matching target/source component pair.
    for target,source in ((130001,150001),(160001,250001)):
        left=next((i for i,p in enumerate(parts) if _word(p,0x338)==target),None)
        right=next((i for i,p in enumerate(parts) if _word(p,0x338)==source),None)
        if left is not None and right is not None:
            quality=struct.unpack_from('<f',parts[left],0x1c)[0]
            bonus=struct.unpack_from('<f',parts[right],0x1c)[0]
            updated=bytearray(parts[left]);struct.pack_into('<f',updated,0x1c,(bonus*f32(.01)+1.)*quality)
            parts[left]=bytes(updated)
    image=finalize_loaded_configuration(image,components_loaded=True)
    image=finalize_engine_configuration(image,templates,engine_components_loaded=True)
    return AssemblyResult(1,image,tuple(parts),tuple(calls))
