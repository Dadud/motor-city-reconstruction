"""Connected recovered owner startup phases with explicit external observations.

This is a bounded composition of already translated original phases, not the
whole 0x43a990 loader: callers still provide selected resources, finalized
configuration, prepared model, prior owner geometry, and the projected-area
scene nodes produced by the live render registry.
"""
from dataclasses import dataclass
import struct

from client.body_startup import prepare_startup_body
from client.owner_wheel_setup import initialize_owner_wheels
from client.scene_area_measure import scene_area_from_nodes
from client.startup_record import construct_startup_record

OWNER_SIZE = 0x2000
CONFIG_SIZE = 0x820


@dataclass(frozen=True)
class OwnerStartupResult:
    owner: bytes
    startup_record: bytes
    scene_area: float


def initialize_owner_startup(owner, configuration, model_image, model_half_extents,
                             scene_nodes, identity, *, assembly_finalized):
    """Run connected body, record, and wheel startup phases in caller order.

    `owner` must contain original prior geometry/state; `configuration` must be
    the complete assembled image; `model`, its half extents, and ordered scene
    nodes must come from the original model/resource preparation chain. This
    function deliberately does not infer any of those observations from stock
    marker spacing, authored display placement, or prototype simulation.
    """
    if assembly_finalized is not True:
        raise ValueError('complete mechanical assembly first')
    if len(owner) != OWNER_SIZE or len(configuration) != CONFIG_SIZE:
        raise ValueError('expected complete owner and finalized configuration images')
    if model_image is None or not isinstance(scene_nodes, (tuple, list)) or not scene_nodes:
        raise ValueError('prepared marker model and ordered live scene nodes required')

    area = scene_area_from_nodes(scene_nodes)
    body = prepare_startup_body(owner, configuration, model_half_extents,
                                identity, assembly_finalized=True)
    record, code = construct_startup_record(body, configuration, model_image,
                                            area_query=area)
    if code != 1:
        raise ValueError(f'original startup-record stage failed with {code}')
    published = bytearray(body)
    published[0x17ec:0x1c94] = record
    wheels = initialize_owner_wheels(published, configuration,
                                     assembly_finalized=True)
    if wheels[0x17ec:0x1c94] != record:
        raise AssertionError('wheel setup unexpectedly changed the published startup record')
    if len(wheels) != OWNER_SIZE:
        raise AssertionError('owner startup produced an incomplete owner image')
    return OwnerStartupResult(wheels, record, struct.unpack('<f', struct.pack('<f', area))[0])
