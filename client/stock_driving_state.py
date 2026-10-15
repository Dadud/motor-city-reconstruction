"""Read-only stock inputs and explicit gaps before recovered driving startup.

This module never instantiates a driving state using its research defaults.
Catalogue component facts, model geometry and authored placement are separate.
"""
from dataclasses import asdict, dataclass, fields
import math

from client.simulation_inputs import build_stock_simulation_inputs


def state_types():
    """Schemas needed by recovered stages; defaults are comparison conveniences."""
    from client.vehicle_update import VehicleUpdateState, UpdateWheel
    from client.engine_update import EngineUpdateState
    from client.driving_engine_rpm import DrivingEngineRPM
    from client.normal_load import NormalLoadInput
    from client.load_transfer import LoadTransferInput
    from client.brake_forces import BrakeForceState, BrakeForceWheel
    from client.brake_thermal import BrakeThermalState, BrakeThermalAxle, BrakeWorkWheel
    from client.tire_update import TireUpdateState, TireWheel, TireCurves
    from client.drivetrain_stages import DriveState,DriveWheel,DriveConfig
    return dict(controller=VehicleUpdateState, controller_wheel=UpdateWheel,
        engine=EngineUpdateState, engine_rpm=DrivingEngineRPM, normal_load=NormalLoadInput,
        load_transfer=LoadTransferInput, brakes=BrakeForceState, brake_wheel=BrakeForceWheel,
        brake_thermal=BrakeThermalState, brake_axle=BrakeThermalAxle, brake_work_wheel=BrakeWorkWheel,
        tires=TireUpdateState, tire_wheel=TireWheel, tire_curves=TireCurves,
        drivetrain=DriveState,drivetrain_wheel=DriveWheel,drivetrain_config=DriveConfig)


class MissingDrivingInputs(ValueError):
    def __init__(self, subsystem, missing):
        self.subsystem = subsystem
        self.missing = tuple(missing)
        super().__init__(f'{subsystem}: explicit original observations required: '+', '.join(self.missing))


def construct_observed_state(subsystem, observations):
    """Construct a recovered record only with every field explicitly supplied.

    Nested records must themselves be constructed explicitly. This checks input
    completeness; stage-specific validation still runs in the recovered stage.
    It does not attest that caller-supplied observations have original evidence.
    """
    schemas = state_types()
    if subsystem not in schemas:
        raise ValueError('unknown recovered driving subsystem')
    if not isinstance(observations, dict):
        raise ValueError('explicit field observation mapping required')
    schema = schemas[subsystem]
    names = {item.name for item in fields(schema)}
    extra = set(observations)-names
    if extra:
        raise ValueError('unknown observation fields: '+', '.join(sorted(extra)))
    missing = sorted(names-set(observations))
    if missing:
        raise MissingDrivingInputs(subsystem, missing)
    nested = {
        'controller': {'wheels': ('controller_wheel', 4)},
        'engine': {'rpm_state': ('engine_rpm', None)},
        'brakes': {'thermal': ('brake_thermal', None), 'wheels': ('brake_wheel', 4)},
        'brake_thermal': {'front': ('brake_axle', None), 'rear': ('brake_axle', None),
                          'wheels': ('brake_work_wheel', 4)},
        'tires': {'wheels': ('tire_wheel', 4), 'front_curves': ('tire_curves', None),
                  'rear_curves': ('tire_curves', None)},
        'drivetrain': {'wheels': ('drivetrain_wheel', 4)},
    }
    for name, (kind, count) in nested.get(subsystem, {}).items():
        value = observations[name]
        if count is None:
            valid = isinstance(value, schemas[kind])
        else:
            valid = isinstance(value, (tuple, list)) and len(value) == count and all(
                isinstance(item, schemas[kind]) for item in value)
        if not valid:
            raise ValueError(f'{subsystem}.{name}: explicitly constructed {kind} records required')
    return schema(**observations)


@dataclass(frozen=True)
class StockDrivingBindings:
    vehicle_id: int
    vehicle_name: str
    components: dict
    recovered_body_configuration: dict
    decoded_geometry: dict
    authored_placement: dict
    unresolved: dict

    @property
    def ready_for_recovered_driving(self):
        return not self.unresolved

    def require_recovered_driving(self):
        if self.unresolved:
            raise MissingDrivingInputs('stock startup', self.unresolved)
        return self

    def report(self):
        output = asdict(self)
        output['ready_for_recovered_driving'] = self.ready_for_recovered_driving
        output['required_explicit_fields'] = {
            name: [item.name for item in fields(schema)] for name, schema in state_types().items()}
        return output


def build_stock_driving_bindings(catalogue, vehicle, world, body_configuration=None):
    """Bind verified stock component fields without inventing assembled config.

    Wheel marker dimensions can be measured, but their equivalence to initialized
    owner/configuration dimensions is unproven. The supplied world pose comes
    from authored clearance placement, not original suspension settling.
    """
    simulation = build_stock_simulation_inputs(catalogue, vehicle, world.rig)
    dimensions = catalogue.tire_dimensions(vehicle)
    suspension = catalogue.suspension(vehicle)
    engine = catalogue.engine_block(vehicle)
    centers = tuple(tuple(v for v in point) for point in world.rig.centers)
    if len(centers) != 4 or any(len(point) != 3 for point in centers):
        raise ValueError('four decoded wheel markers required')
    if not all(math.isfinite(v) for point in centers for v in point):
        raise ValueError('finite decoded wheel markers required')
    if len(world.contacts) != 4 or tuple(c.wheel for c in world.contacts) != ('LF', 'RF', 'LR', 'RR'):
        raise ValueError('four ordered LF/RF/LR/RR placement observations required')
    geometry = dict(wheel_centers=centers, marker_wheelbase_m=simulation.wheelbase_m,
        front_marker_track_m=abs(centers[0][0]-centers[1][0]),
        rear_marker_track_m=abs(centers[2][0]-centers[3][0]),
        original_configuration_binding_verified=False)
    body = {} if body_configuration is None else dict(
        part_type_id=body_configuration.part_type_id,
        physics_ordinal=body_configuration.physics_ordinal,
        body_base_mass=body_configuration.body_mass,
        wheelbase=body_configuration.wheelbase,
        front_track=body_configuration.front_track,
        rear_track=body_configuration.rear_track,
        front_weight_fraction=body_configuration.body_front_weight_fraction,
        front_clearance_reference=body_configuration.front_clearance_reference,
        rear_clearance_reference=body_configuration.rear_clearance_reference,
        final_assembled_configuration_verified=False)
    components = dict(engine_block=asdict(engine), wheels={})
    for key in ('LF', 'RF', 'LR', 'RR'):
        spring, shock = suspension[key]
        components['wheels'][key] = dict(tire=asdict(dimensions[key]),
            tire_radius_m=dimensions[key].radius, stance_adjustment_m=dimensions[key].stance_adjustment,
            spring=asdict(spring), shock=asdict(shock))
    # These known constants apply to scheduler/motion helpers, not a guessed tick.
    components['timing'] = dict(simulation_step_s=simulation.simulation_step_s,
        pose_step_s=simulation.pose_step_s, support_lookahead_s=simulation.support_lookahead_s)
    placement = dict(position=world.pose.position, rotation=world.pose.rotation,
        contacts=tuple(dict(wheel=c.wheel, center=c.center, height=c.height,
                            normal=c.normal, vertical_gap=c.gap,
                            decoded_surface=None if c.surface is None else
                                (c.surface.block, c.surface.descriptor)) for c in world.contacts),
        original_spawn_verified=False, support_flags_verified=False)
    unresolved = dict(
        configuration='Body initialization, fourteen component loaders including tire templates, and numeric postload are available; finish remaining loaders, engine curves, full dispatch/quality and initialized owner binding.',
        mass_inertia='Whole-car mass, gravity parameter, centre of mass, inverse mass and rotational inertia are not engine-block mass or mesh bounds.',
        geometry='Body configuration supplies catalogue wheelbase/tracks; verify final owner binding, front/rear levers, area/height and transforms.',
        contacts='Recover original spawn/settling and contact flags, wheel scales, support corrections and surface coefficient lookup; clearance gaps are not suspension compression.',
        engine='Supply final assembled torque knots, idle/max/limiter RPM and initialized dispatcher fields. Transmission/rear-end loaders now produce ratios, losses and final drive; complete remaining component and rear-tire loading before final gear binding.',
        drivetrain='Supply original clutch/gear/differential state, assembled ratios and effect consumers; do not substitute prototype gearing.',
        brakes='Bind original brake material, thermal/cooling/capacity parameters, distribution, quality, component codes and initial temperatures/countdowns.',
        tires='Bind two complete 26-knot axle response curves, angle coefficients, grip/quality/wear, steering limits and native spin scales.',
        observations='Supply original input/service gates, counters/flags, track weather/mode queries and ordered nearby vehicle records.',
        controller='Connect recovered children on shared owner state and recover remaining stages; every callback must execute real recovered behavior.')
    return StockDrivingBindings(vehicle.branded_id, vehicle.name, components, body, geometry, placement, unresolved)


def load_stock_driving_bindings(game, vehicle_id=101, track='drag'):
    """Load external original assets without writing the installation directory."""
    from client.assets import Assets
    from client.catalogue import Catalogue
    from client.world import load_world_vehicle
    from client.body_configuration import stock_body_configuration
    if not isinstance(track, str) or not track or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in track):
        raise ValueError('lowercase track directory identifier required')
    assets = Assets(game)
    catalogue = Catalogue.load(assets.paths['data/db/online.mdb'])
    vehicle = catalogue.vehicle(vehicle_id)
    track_bytes = assets.paths[f'data/tracks/{track}/tr.frd'].read_bytes()
    world = load_world_vehicle(assets, catalogue, vehicle, track_bytes)
    return build_stock_driving_bindings(catalogue, vehicle, world,
                                       stock_body_configuration(catalogue, vehicle_id))
