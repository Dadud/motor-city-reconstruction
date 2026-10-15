"""Inspect complete supported mechanical assembly, without inventing owner state."""
import argparse
import json
from pathlib import Path
from client.catalogue import Catalogue
from client.dyno import load_flow_templates
from client.mechanical_assembly import assemble_stock_vehicle,assembly_report
from client.tire_templates import load_tire_templates


def inspect(database,executable,vehicle,*,percent_damage,item_wear):
    catalogue=Catalogue.load(database)
    result=assemble_stock_vehicle(catalogue,vehicle,load_flow_templates(executable),
        tire_templates=load_tire_templates(database),percent_damage=percent_damage,item_wear=item_wear)
    return dict(vehicle_id=vehicle,name=catalogue.vehicle(vehicle).name,
        fixture_state=dict(percent_damage=percent_damage,item_wear=item_wear),
        **assembly_report(result))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('database',type=Path)
    p.add_argument('executable',type=Path);p.add_argument('--vehicle',type=int,default=101)
    p.add_argument('--damage',type=int,required=True);p.add_argument('--wear',type=int,required=True)
    a=p.parse_args();print(json.dumps(inspect(a.database,a.executable,a.vehicle,
        percent_damage=a.damage,item_wear=a.wear),indent=2))
