"""Original startup force helper 0x538660 and acceleration tables 0x5384f0."""
import math
import struct
from client.engine_update import curve_torque_at_rpm
from client.tire_response import f32


def _inputs(configuration,record):
    if len(configuration)!=0x820 or len(record)!=0x4a8:
        raise ValueError('complete configuration and startup table record required')
    def get(data,offset):return f32(struct.unpack_from('<f',data,offset)[0])
    maximum=struct.unpack_from('<i',configuration,0x70)[0]
    if not 0<maximum<=12000:raise ValueError('maximum RPM in [1,12000] required')
    denominator=get(record,0x104)
    if denominator<=0:raise ValueError('positive startup denominator required')
    return get,maximum,denominator


def startup_force(configuration,record,rpm,selector,sample,secondary=False):
    """Complete finite 0x538660; sixth ABI argument is unused by the original."""
    get,maximum,denominator=_inputs(configuration,record)
    if type(rpm)is not int or not 1<=rpm<=12000 or type(selector)is not int or not 0<=selector<8:
        raise ValueError('positive RPM and selector 0..7 required')
    if type(secondary)is not bool:raise ValueError('boolean secondary observation required')
    sample=f32(sample)
    curve=struct.unpack_from('<26f',configuration,0x80)
    torque=f32(curve_torque_at_rpm(curve,rpm))
    fraction=f32(rpm/maximum)
    field=struct.unpack_from('<i',configuration,0x4d8)[0]
    size=f32(field+1.)
    if size<0:raise ValueError('nonnegative original correction range required')
    angular=f32(rpm*f32(6.2831854820251465))
    deduction=f32(size*4*fraction*60000/angular)
    loss=max(0.,min(f32(size*10),deduction))
    field=struct.unpack_from('<i',configuration,0x4f4)[0]
    remainder=f32((torque-loss)-((field+1.)*fraction*2*60000/angular))
    effective=max(0.,remainder)
    if struct.unpack_from('<i',configuration,0x68c)[0]!=0 and 0<=sample<=10:
        t=sample*f32(.1)
        effective=((1-t)*t*t*t*1.5+1)*effective
    ratio=get(configuration,0x334+selector*4)*get(configuration,0x374)
    result=((get(record,0x64+selector*4)*get(configuration,0x6e8)*effective)/
        (ratio*ratio*f32(.0015)+1))/denominator
    if not math.isfinite(result):raise ValueError('finite startup force required')
    return result


def acceleration_table(configuration,record):
    """Return record with only the two original 112-sample output ranges changed."""
    get,_,_=_inputs(configuration,record)
    idle=struct.unpack_from('<i',configuration,0x6c)[0]
    if not 1<=idle<=12000:raise ValueError('idle RPM in [1,12000] required')
    mass=get(configuration,0x20)
    if mass<=0:raise ValueError('positive mass required')
    second=get(configuration,0x3e0)>0 and get(configuration,0x3e4)>0
    result=bytearray(record);index=0;selector=2
    for sample in range(112):
        if get(record,0xac+index*4)<sample:index+=1;selector+=1
        if selector>=8:raise ValueError('startup shift schedule exceeds eight selectors')
        rpm=round(min(12000.,max(f32(idle),f32(sample*get(record,0x2c+index*4)))))
        force=startup_force(configuration,record,rpm,selector,float(sample))
        primary=0. if force<=0 else f32((1./mass)*force)
        struct.pack_into('<f',result,0x128+sample*4,primary)
        other=startup_force(configuration,record,rpm,selector,float(sample),True) if second else force
        secondary=0. if other<=0 else f32((1./mass)*other)
        struct.pack_into('<f',result,0x2e8+sample*4,secondary)
    return bytes(result)
