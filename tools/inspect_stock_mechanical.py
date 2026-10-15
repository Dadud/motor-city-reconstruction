"""Inspect recovered loading with external catalogue data and explicit wear.

Temporary local instance identifiers are authored fixture keys, never server IDs.
This is an incomplete startup comparison fixture, not a playable configuration.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
from client.body_configuration import stock_body_configuration
from client.catalogue import Catalogue
from client.mechanical_loaders import MECHANICAL_LOADERS
from client.mechanical_parts import MechanicalPart,expand_mechanical_parts
from client.owned_parts import OwnedPart


# Original dispatcher order restricted to recovered bodies. All omitted loaders
# remain explicitly unsupported; this list is not a replacement assembly rule.
RECOVERED_ORDER=((160001,0),(1000001,0),(1100001,0),(180001,0),(190001,0),
    (140001,0),(130001,0),
    *((10001,i) for i in (1,2,3,4)),*((12001,i) for i in (1,2,3,4)),
    *((11001,i) for i in (1,2,3,4)),(340001,0),(320001,0),(330001,0),
    (200001,0),(1200001,0),(280001,0),(290001,0),(300001,0),
    (230001,0),(240001,0),(250001,0),
    *((100001,i) for i in (1,2,4,3)),*((110001,i) for i in (1,2,4,3)))


def stock_slots(catalogue,vehicle_id,*,percent_damage,item_wear):
    """Join actual part/Physics ordinal 1 rows with supplied fixture state."""
    slots=[]
    for index,part in enumerate(catalogue.vehicle(vehicle_id).parts):
        instance=OwnedPart(index+1,part.branded_id,percent_damage,item_wear,0,0,0)
        slot=bytearray(catalogue.owned_part_intermediate(instance,text_encoding='cp1252'))
        struct.pack_into('<i',slot,0x61c,part.attachment_id)
        slots.append(bytes(slot))
    return tuple(slots)


def selected_parts(parts):
    """Select known dispatcher entries and apply its pre-loader quality reset."""
    for kind,attachment in RECOVERED_ORDER:
        for part in parts:
            if struct.unpack_from('<I',part.image,0x338)[0]==kind and (attachment==0 or part.attachment==attachment):
                image=bytearray(part.image);struct.pack_into('<f',image,0x1c,1.)
                yield kind,MechanicalPart(part.source_index,part.attachment,bytes(image))
                break


def inspect(catalogue,vehicle_id,*,percent_damage,item_wear,tire_templates=None):
    source=stock_slots(catalogue,vehicle_id,percent_damage=percent_damage,item_wear=item_wear)
    parts=expand_mechanical_parts(source)
    configuration=stock_body_configuration(catalogue,vehicle_id).image
    loaded=[]
    for kind,part in selected_parts(parts):
        result=(MECHANICAL_LOADERS[kind](configuration,part.image,tire_templates)
            if kind==110001 else MECHANICAL_LOADERS[kind](configuration,part.image))
        configuration=result.configuration
        loaded.append(dict(abstract_type_id=kind,source_index=part.source_index,
            attachment=part.attachment,status=result.status,
            component_quality=struct.unpack_from('<f',result.component,0x1c)[0]))
    unknown=Counter(struct.unpack_from('<I',part.image,0x338)[0]
        for part in parts if struct.unpack_from('<I',part.image,0x338)[0] not in MECHANICAL_LOADERS
        and struct.unpack_from('<I',part.image,0x338)[0]!=20001)
    return dict(vehicle_id=vehicle_id,source_slots=len(source),mechanical_components=len(parts),
        fixture_state=dict(percent_damage=percent_damage,item_wear=item_wear,
            local_instance_ids='authored fixture keys; not server identities'),
        body_numeric_initializer_only=True,assembly_complete=False,ready_for_recovered_driving=False,
        recovered_loader_results=loaded,unrecovered_component_counts=dict(sorted(unknown.items())),
        partial_mass_accumulator=struct.unpack_from('<f',configuration,0x20)[0],
        mass_is_complete=False,
        tire_templates_supplied=tire_templates is not None,
        assembled_axles={name:dict(width_mm=struct.unpack_from('<f',configuration,0x124+shift)[0],
            lateral_curve=struct.unpack_from('<26f',configuration,0x150+shift),
            aligning_curve=struct.unpack_from('<26f',configuration,0x1b8+shift))
            for name,shift in (('front',0),('rear',0x104))} if tire_templates is not None else None,
        transmission=dict(gear_count=struct.unpack_from('<i',configuration,0x32c)[0],
            ratios=struct.unpack_from('<8f',configuration,0x334),
            losses=struct.unpack_from('<8f',configuration,0x354),
            final_drive=struct.unpack_from('<f',configuration,0x374)[0]),
        pending='remaining loaders, complete dispatch/quality/finalization, geometry and owner startup')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('database',type=Path)
    parser.add_argument('--vehicle',type=int,default=101)
    parser.add_argument('--damage',type=int,required=True);parser.add_argument('--wear',type=int,required=True)
    args=parser.parse_args()
    from client.tire_templates import load_tire_templates
    print(json.dumps(inspect(Catalogue.load(args.database),args.vehicle,
        percent_damage=args.damage,item_wear=args.wear,
        tire_templates=load_tire_templates(args.database)),indent=2))
