"""Recovered unboosted 0x46d1d0 path for ordinary carburetors.

Complete mechanical assembly is a separate responsibility. This internal adapter
requires loaded engine inputs, external flow templates and the recovered core.
Special carburetor six and boost remain explicit unsupported branches.
"""
import math
import struct
from client.dyno import build_dyno_record
from client.engine import EngineBlock,CylinderHead,Camshaft,ValveTrain
from client.cylinder_solver import solve_core_record
from client.tire_response import f32


def _number(image,offset):
    value=struct.unpack_from('<f',image,offset)[0]
    if not math.isfinite(value):raise ValueError('finite engine configuration required')
    return value


def _integer(image,offset):return struct.unpack_from('<i',image,offset)[0]


def build_assembled_core_record(configuration,templates):
    if len(configuration)!=0x820:raise ValueError('expected assembled configuration image')
    n=lambda offset:_number(configuration,offset)
    i=lambda offset:_integer(configuration,offset)
    if n(0x378)!=0 or n(0x3d8)!=0:
        raise ValueError('boosted engine finalization is not recovered')
    if not 0<=i(0x3c8)<=5:raise ValueError('special carburetor finalization is not recovered')
    block=EngineBlock(n(0x430),n(0x434),n(0x438),i(0x43c),n(0x428))
    head=CylinderHead(i(0x50c),i(0x514),i(0x510),n(0x518),n(0x54),n(0x524),n(0x528),n(0x504))
    cam=Camshaft(i(0x534),i(0x538),n(0x53c),n(0x544),n(0x548),
        tuple(n(o) for o in (0x54c,0x550,0x554,0x558)),n(0x52c))
    train=ValveTrain(i(0x564),n(0x568),n(0x55c))
    template=templates[head.flow_template_id(block.bore_m,i(0x440))]
    modifier=n(0x518)-n(0x3f4)+n(0x5b0)+n(0x400)
    template=template.scaled(modifier)
    kind=i(0x57c)
    exhaust=(1,2,3 if n(0x5a0)!=0 else 4,5 if n(0x5a0)!=0 else 6)[kind] if 0<=kind<4 else 1
    capacity=math.trunc(n(0x3d0)*n(0x3cc))
    return build_dyno_record(block,head,cam,train,template,
        intake_mode=i(0x3ac)+1,intake_flow=n(0x3b4),exhaust_mode=exhaust,
        exhaust_flow=n(0x584),carb_capacity=capacity,carb_code=2 if i(0x3c8) in (0,1) else 4)


def _capacity(image,factor=1.):
    n=lambda offset:_number(image,offset)
    radius=n(0x430)*f32(.5)
    value=n(0x434)*radius*radius*f32(3.1415927)*_integer(image,0x43c)
    value=value*f32(1e6)*f32(.061024)*f32(.0005787037)
    value=value*(_integer(image,0x70)-500)*f32(.5)*f32(factor)
    return max(100.,f32(value))


def _power_candidate(index,torque):return index*torque*f32(52.35988)*f32(.001)


def _exhaust_correction(image,curve):
    peak=0.;index=0
    for k,t in enumerate(curve):
        candidate=_power_candidate(k,t)
        if candidate>peak:peak=f32(candidate);index=k
    if peak<=0:return tuple(f32(t*f32(1.01)) for t in curve)
    raw=f32((((_number(image,0x59c)+peak)*f32(60000.))/(index*f32(3141.5928)))/curve[index]-1.)
    gain=min(f32(.1),max(0.,raw))+1.
    return tuple(f32(t*gain) for t in curve)


def correct_curve_limits(configuration,curve):
    """Original exhaust, electrical and valve-RPM corrections in call order."""
    if len(configuration)!=0x820 or len(curve)!=25 or not all(math.isfinite(t) for t in curve):
        raise ValueError('finite 25-point curve and assembled configuration required')
    curve=tuple(map(f32,curve))
    if _number(configuration,0x59c)>0 and _number(configuration,0x58c)>0:
        curve=_exhaust_correction(configuration,curve)
    peak=0.
    for index in range(4,25):peak=max(peak,f32(_power_candidate(index,curve[index])))
    insufficient_rpm=_integer(configuration,0x4cc)<_integer(configuration,0x70)-500
    insufficient_power=_number(configuration,0x4d0)<peak
    factor=f32(.85 if insufficient_rpm and insufficient_power else .95 if insufficient_rpm or insufficient_power else 1.)
    curve=tuple(f32(t*factor) for t in curve)
    limit=_integer(configuration,0x570)
    return tuple(f32(t*(limit/(rpm+500))**2) if limit<rpm else t
        for t,rpm in zip(curve,range(0,12500,500)))


def finalize_engine_configuration(configuration,templates,*,engine_components_loaded,solver=solve_core_record):
    """Generate the normal unboosted engine curve and limits from loaded fields.

    The assertion describes engine inputs only; it never certifies whole-car
    assembly. A supplied solver is an explicit comparison seam, not a fallback.
    """
    if engine_components_loaded is not True:raise ValueError('load complete engine components first')
    core=solver(build_assembled_core_record(configuration,templates))
    image=bytearray(configuration)
    n=lambda offset:_number(image,offset)
    def put(offset,value):struct.pack_into('<f',image,offset,value)
    def integer(offset,value):struct.pack_into('<i',image,offset,value)
    compression=0.
    if n(0x54)<6:
        delta=n(0x54)-6
        compression=min(0.,max(f32(-.2),f32(delta*f32(.0675)-delta*delta*f32(.005))))
    carb=0.
    if n(0x3cc)<300:
        carb=min(0.,max(f32(-.3),f32((n(0x3cc)-300)*f32(.0015))))
    factor=f32(carb+compression+1.)
    curve=[0.]*25
    for k,torque in enumerate(struct.unpack_from('<19f',core,0x110)):
        curve[k+4]=max(0.,f32(torque*f32(1.3558)*factor))
    power=f32(2000*curve[4]*f32(.00010471976))
    curve[2]=f32(f32(power*f32(.33333334))*f32(9.549296))
    curve[3]=f32(power*f32(.6666667)*f32(6.3661976))
    curve[24]=0.
    curve=correct_curve_limits(image,curve)
    threshold=min(180.,max(90.,f32(max(0.,*curve[4:])*f32(.35))))
    crossing=next((k for k in range(1,25) if curve[k]>=threshold),None)
    if crossing is None or curve[crossing]==curve[crossing-1]:
        raise ValueError('engine curve has no safe original idle crossing')
    left=curve[crossing-1]
    rpm=f32(crossing*500-500+((threshold-left)*500)/(curve[crossing]-left))
    idle=min(3000,max(500,math.trunc(round(rpm)/25)*25))+150
    integer(0x6c,idle)
    pressures=struct.unpack_from('<19f',core,0x15c)
    minimum=pressures[0];maximum_index=0
    for k,pressure in enumerate(pressures):
        if pressure<=minimum:minimum=pressure;maximum_index=k+4
    maximum_index+=1;integer(0x70,maximum_index*500)
    curve=tuple(t if k<maximum_index else 0. for k,t in enumerate(curve))
    required=_capacity(image)
    if required<n(0x3cc):
        ratio=max(f32(.6),f32(required/n(0x3cc)))
        altered=bytearray(core);struct.pack_into('<h',altered,0xa4,math.trunc(ratio*n(0x3cc)))
        core=solver(bytes(altered))
        curve=tuple(f32(t*ratio) for t in curve)
    struct.pack_into('<25f',image,0x80,*curve)
    put(0x78,max(struct.unpack_from('<19f',core,0x1a8)))
    return bytes(image)
