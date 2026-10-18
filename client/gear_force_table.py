"""Complete bounded 0x53b260 producer; 135 force samples for one gear."""
import struct
from client.engine_update import curve_torque_at_rpm
from client.tire_response import f32


def gear_force_table(configuration, rpm_steps, selector):
    """Read an assembled configuration; return the original binary32 samples.

    rpm_steps is the caller's eight-element RPM-per-sample table, not a network
    or simulation rate. The torque lookup is the recovered 0x548f00 child.
    """
    if len(configuration) != 0x820:
        raise ValueError('complete 0x820-byte configuration required')
    if type(selector) is not int or not 0 <= selector < 8 or len(rpm_steps) != 8:
        raise ValueError('eight RPM steps and selector in [0,7] required')
    steps=tuple(map(f32,rpm_steps))
    def get(offset): return f32(struct.unpack_from('<f',configuration,offset)[0])
    idle,maximum=struct.unpack_from('<ii',configuration,0x6c)
    if not 0 <= idle <= maximum <= 12000:
        raise ValueError('ordered RPM bounds in [0,12000] required')
    curve=struct.unpack_from('<26f',configuration,0x80)
    for value in curve: f32(value)
    radius=f32(((get(0x228)*f32(.001))*(get(0x22c)*f32(.01))*2+
        get(0x230)*f32(.0254))*.5)
    if radius <= 0: raise ValueError('positive rear tire radius required')
    gear=get(0x334+selector*4); final=get(0x374)
    multiplier=f32(get(0x354+selector*4)*gear*final)
    ratio=gear*final
    correction=max(1.,min(1.5,f32(ratio*f32(.0025)*ratio+1.)))
    result=[]
    for index in range(135):
        rpm=max(0.,min(12000.,f32(index*steps[selector])))
        if not idle <= rpm <= maximum: result.append(0.);continue
        force=f32(curve_torque_at_rpm(curve,round(rpm))*multiplier)
        result.append(f32(force/(correction*radius)))
    return tuple(result)
