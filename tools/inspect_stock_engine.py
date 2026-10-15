"""Inspect recovered ordinary unboosted engine curves from external game files."""
import argparse
import json
from pathlib import Path
import struct
from client.catalogue import Catalogue
from client.dyno import load_flow_templates
from client.engine_curve import finalize_engine_configuration
from tools.engine_curve_oracle import loaded_engine


def inspect(catalogue,executable,vehicle):
    image=loaded_engine(catalogue,vehicle)
    final=finalize_engine_configuration(image,load_flow_templates(executable),engine_components_loaded=True)
    curve=struct.unpack_from('<25f',final,0x80)
    return dict(vehicle_id=vehicle,name=catalogue.vehicle(vehicle).name,
        fixture_state=dict(percent_damage=0,item_wear=0),
        idle_rpm=struct.unpack_from('<i',final,0x6c)[0],
        maximum_rpm=struct.unpack_from('<i',final,0x70)[0],
        torque_curve=[dict(rpm=k*500,torque=t) for k,t in enumerate(curve)],
        torque_units='original converted torque field; 1.3558 multiplier retained',
        assembly_complete=False,ready_for_recovered_driving=False,
        pending='remaining vehicle loaders, dispatch/quality, geometry, owner startup and integrated driving')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('database',type=Path);p.add_argument('executable',type=Path)
    p.add_argument('--vehicle',type=int,default=101);a=p.parse_args()
    print(json.dumps(inspect(Catalogue.load(a.database),a.executable,a.vehicle),indent=2))
