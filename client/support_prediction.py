"""Complete 0x53d320 owner arithmetic with an explicit terrain projection boundary.

Surface queries return their record AND aliased reference-point writes. They do
not silently use the prototype nearest-height or wheel-radius contact rules.
"""
from dataclasses import dataclass,replace
from client.tire_response import f32

IDENTITY=(1.,0.,0.,0.,1.,0.,0.,0.,1.)

@dataclass(frozen=True)
class SupportRecord:
    sector: int = 0
    group: int = 0
    status: int = 0
    surface_id: int | None = None
    vertex_ids: tuple = (None,None,None,None)
    surface_code: int | None = None

@dataclass(frozen=True)
class PredictionWheel:
    local_point: tuple
    world_point: tuple
    clear_reference: float
    record: SupportRecord = SupportRecord()
    support_delta: float = 0
    contact: bool = False
    surface_class: int = 0
    query_tail: bytes | None = None

@dataclass(frozen=True)
class SupportPredictionState:
    wheels: tuple
    position: tuple
    velocity: tuple
    to_world: tuple = IDENTITY
    context: int = 0
    fallback_surface: int = 0
    support_count: int = 0

@dataclass(frozen=True)
class SupportQuery:
    slot: int
    point: tuple
    context: int
    previous_world: tuple
    record: SupportRecord = SupportRecord()
    query_tail: bytes | None = None

@dataclass(frozen=True)
class SupportProjection:
    point: tuple
    reference_position: tuple
    record: SupportRecord
    query_tail: bytes | None = None

@dataclass(frozen=True)
class SupportPredictionOutput:
    state: SupportPredictionState
    queries: tuple

def _vector(v):
    if len(v)!=3:raise ValueError('three-component point required')
    return tuple(map(f32,v))

def _integer(value,low,high):
    if type(value) is not int or not low<=value<=high:raise ValueError('integer observation outside supported range')

def _record(r):
    if not isinstance(r,SupportRecord):raise ValueError('typed support record required')
    _integer(r.sector,-2147483648,2147483647);_integer(r.group,-2147483648,2147483647);_integer(r.status,0,0xffffffff)
    if len(r.vertex_ids)!=4:raise ValueError('four vertex identities required')
    for identity in (r.surface_id,*r.vertex_ids):
        if identity is not None:_integer(identity,0,0xffffffff)
    if r.surface_id is None:
        if r.surface_code is not None:raise ValueError('surface code requires surface identity')
    elif r.surface_code is None:raise ValueError('surface identity requires observed descriptor byte')
    else:_integer(r.surface_code,0,255)
    return r

def predict_support(state,project):
    """Four original wheel records, ordered queries and exact contact comparison.

    project(SupportQuery) must supply SupportProjection. Its reference_position
    is the query helper's aliased record-position output, not a guessed previous
    position. Missing terrain behavior must be supplied explicitly.
    """
    if not callable(project):raise ValueError('terrain projection executor required')
    if len(state.wheels)!=4 or len(state.to_world)!=9:raise ValueError('four wheels and nine-element matrix required')
    _integer(state.context,-2147483648,2147483647);_integer(state.fallback_surface,0,31)
    position,velocity=_vector(state.position),_vector(state.velocity);matrix=tuple(map(f32,state.to_world))
    lookahead=tuple(f32(p+v*f32(1/48)) for p,v in zip(position,velocity))
    wheels=[];queries=[];count=0
    for slot,w in enumerate(state.wheels):
        local,previous=_vector(w.local_point),_vector(w.world_point);reference=f32(w.clear_reference)
        if reference<0:raise ValueError('nonnegative contact reference required')
        _record(w.record)
        # Original scalar dispatch sets x87 precision to 24 significant bits:
        # each multiply and add rounds, including the final translation.
        point=tuple(f32(f32(f32(f32(local[0]*matrix[i])+f32(local[1]*matrix[3+i]))+
                                      f32(local[2]*matrix[6+i]))+lookahead[i]) for i in range(3))
        query=SupportQuery(slot,point,state.context,previous,w.record,w.query_tail);queries.append(query)
        projection=project(query)
        if not isinstance(projection,SupportProjection):raise ValueError('typed terrain projection required')
        projected=_vector(projection.point);query_reference=_vector(projection.reference_position);record=_record(projection.record)
        tail = w.query_tail if projection.query_tail is None else projection.query_tail
        if tail is not None and (not isinstance(tail, bytes) or len(tail) != 24):
            raise ValueError('24-byte aliased query tail required')
        delta=f32(projected[1]-query_reference[1])
        contact=delta>=-reference;count+=int(contact)
        surface=state.fallback_surface if record.surface_id is None else record.surface_code&31
        wheels.append(replace(w,local_point=local,world_point=projected,clear_reference=reference,
            record=record,query_tail=tail,support_delta=delta,contact=contact,surface_class=surface))
    return SupportPredictionOutput(replace(state,wheels=tuple(wheels),position=position,velocity=velocity,
        to_world=matrix,support_count=count),tuple(queries))
