"""Place a stock vehicle in decoded track terrain using explicit local assets."""
from dataclasses import dataclass
import math

from .contact import Pose, WheelRig
from .fce import Model
from .engine import EngineBlock
from .scene import stock_scene
from .track import decode_track
from .track_surface import TrackSurface, decode_surface


@dataclass(frozen=True)
class WorldVehicle:
    model: Model
    textures: tuple
    flags: int
    notes: tuple
    pose: Pose
    rig: WheelRig
    radii: dict
    contacts: tuple
    terrain: TrackSurface
    engine: EngineBlock


def load_world_vehicle(assets, catalogue, vehicle, track_bytes, skin=None):
    path = assets.paths.get(f'data/models/{vehicle.body_filename}.viv'.casefold())
    if path is None:
        raise ValueError(f'stock body archive missing: {vehicle.body_filename}')
    body = assets.load_vehicle(path)
    rig = WheelRig.from_model(body)
    model, textures, flags, notes = stock_scene(assets, path, vehicle, skin)
    dimensions = catalogue.tire_dimensions(vehicle)
    radii = {key: tire.radius for key, tire in dimensions.items()}
    terrain = decode_surface(track_bytes)
    road = decode_track(track_bytes).slices[0]
    initial = Pose.yaw(road.position, math.atan2(road.forward[0], road.forward[2]))
    pose, contacts = rig.spawn_pose(terrain, initial, radii)
    engine = catalogue.engine_block(vehicle)
    return WorldVehicle(model, textures, flags, notes, pose, rig, radii, contacts, terrain, engine)


def pose_matrix(pose):
    """Column-major OpenGL transform matching Pose.transform exactly."""
    return (
        pose.rotation[0][0], pose.rotation[1][0], pose.rotation[2][0], 0,
        pose.rotation[0][1], pose.rotation[1][1], pose.rotation[2][1], 0,
        pose.rotation[0][2], pose.rotation[1][2], pose.rotation[2][2], 0,
        *pose.position, 1)
