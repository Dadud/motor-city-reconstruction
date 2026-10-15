"""Original startup load, balance and brake producers; units remain under study.

Configuration fields and wheel response tables are original producer inputs.
These helpers do not establish the complete suspension/handling model.
"""
import math
import struct
from client.tire_response import f32,wheel_response,WheelCurveInput


def _read(configuration):
    if len(configuration)!=0x820:raise ValueError('complete configuration image required')
    def number(offset):
        value = struct.unpack_from('<f', configuration, offset)[0]
        if not math.isfinite(value):
            raise ValueError('finite configuration observations required')
        return value
    return number


def startup_load_coefficient(configuration):
    n=_read(configuration)
    mass=n(0x20)-n(0x28);height=n(0x38)
    denominator=(n(0x104)+n(0xfc))-height*f32(.3181818127632141)*mass*f32(.17121680080890656)
    if denominator==0:raise ValueError('nonzero startup load denominator required')
    return f32((height*f32(.9090908765792847)*mass*f32(9.8100004196167))/denominator)


def startup_balance_coefficient(configuration,*,alternate_load=False):
    n=_read(configuration)
    if min(n(0x2c),n(0x30),n(0x34),n(0x144),n(0x248))<=0:
        raise ValueError('positive wheelbase, tracks and tire template widths required')
    coefficient=startup_load_coefficient(configuration)
    wheelbase=n(0x2c)
    # Original 0x6f1430 returns turn units using this stored double constant.
    angle=f32(math.atan2(wheelbase,33.)*.15915493667125702)
    angle_scale=angle*360.
    if angle_scale==0:raise ValueError('nonzero angular scale required')
    def axle(front):
        lever=f32(wheelbase*n(0x3c)) if front else f32((1.-n(0x3c))*wheelbase)
        weight=f32(((n(0x20)*f32(4.90500020980835))/wheelbase)*lever)
        ratio=f32(n(0x124 if front else 0x228)/n(0x144 if front else 0x248))
        surface=max(f32(.9),min(1.5,ratio))
        curve_input=WheelCurveInput(angle,0.,weight,surface)
        offset=0x150 if front else 0x254
        primary=wheel_response(struct.unpack_from('<26f',configuration,offset),n(0x148 if front else 0x24c),curve_input,
                               alternate_load=alternate_load)
        offset=0x1b8 if front else 0x2bc
        secondary=wheel_response(struct.unpack_from('<26f',configuration,offset),n(0x148 if front else 0x24c),curve_input,secondary=True)
        stiffness=f32(primary/angle_scale);secondary=f32(secondary/angle_scale)
        if stiffness==0:raise ValueError('nonzero primary response stiffness required')
        transfer=((coefficient*n(0xfc if front else 0x104)+(weight+weight)*n(0x38)*f32(.45454543828964233))*
                  f32(.29876917600631714))/n(0x30 if front else 0x34)
        displacement=f32(weight/stiffness)
        correction=f32(((transfer*transfer*f32(9.705000411486253e-05))/stiffness)*displacement)
        return displacement,correction,secondary
    front,front_correction,front_secondary=axle(True)
    rear,rear_correction,rear_secondary=axle(False)
    extra=0.
    if front_secondary!=0 and rear_secondary!=0:
        extra=f32(abs((f32(9.8100004196167)/wheelbase)*((rear_secondary+front_secondary)/(rear_secondary*front_secondary))))
    value=f32((front_correction-rear_correction)+(front-rear)+extra)
    return max(-10.,min(10.,value))


def brake_diameter(code):
    """Complete 0x538820 selector, preserving the original stored constants."""
    if type(code) is not int or not 0<=code<=0xffffffff:raise ValueError('uint32 brake code required')
    values=(.20319999754428864,.2159000039100647,.22859999537467957,.24130000174045563,
            .2540000081062317,.26669999957084656,.2793999910354614,.2920999825000763,
            .30480000376701355,.3174999952316284,.3301999866962433,.34290000796318054,
            .3555999994277954,.3682999908924103,.38099998235702515,.3937000036239624,
            .40639999508857727,.41909998655319214,.4318000078201294,.44449999928474426,.45719999074935913)
    return values[code] if code<=20 else values[0]


def brake_capacity(diameter,material,construction,pressure,auxiliary):
    """0x5399d0; retain double result until the caller's original store."""
    if any(type(v) is not int or not 0<=v<=0xffffffff for v in (material,construction)):
        raise ValueError('uint32 brake selectors required')
    if type(auxiliary) is not bool:raise ValueError('boolean auxiliary flag required')
    diameter,pressure=map(f32,(diameter,pressure))
    factor={0:f32(.85),1:f32(.9),2:f32(.95)}.get(material,1.)
    radius=diameter*.5
    value=radius*radius*f32(math.pi)*f32(16.31012725830078)*2500.*factor*pressure
    if construction==1:
        value*=f32(.98)
        if auxiliary:value*=f32(.8)
    if not math.isfinite(value):raise ValueError('finite brake capacity required')
    return value


def startup_brake_balance(configuration):
    """Complete 0x53b040 startup brake-balance calculation."""
    n=_read(configuration)
    def word(offset):return struct.unpack_from('<I',configuration,offset)[0]
    wheelbase=n(0x2c)
    if wheelbase<=0:raise ValueError('positive wheelbase required')
    mass_force=f32(n(0x20)*f32(9.8100004196167))
    per_length=(n(0x20)*f32(9.8100004196167))/wheelbase
    front=f32(wheelbase*n(0x3c)*per_length)
    rear=f32((1.-n(0x3c))*wheelbase*per_length)
    height=f32(n(0x38)*f32(.9090908765792847))
    def capacity(front):
        offset=0x5d0 if front else 0x5f0
        return brake_capacity(brake_diameter(word(offset+8)),word(offset+4),word(offset),1.,False)
    def radius(front):
        offset=0x124 if front else 0x228
        sidewall=(n(offset)*f32(.001))*(n(offset+4)*f32(.01))
        value=(sidewall+sidewall+n(offset+8)*f32(.0254))*.5
        if value<=0:raise ValueError('positive tire radius required')
        return value
    front_capacity=f32(capacity(True)/radius(True))
    if front_capacity==0:raise ValueError('nonzero front brake capacity required')
    ratio=f32((capacity(False)/radius(False))/front_capacity)
    ratio=max(.5,min(1.,ratio))
    front_mu,rear_mu=n(0x140),n(0x244)
    rear_transfer=f32((height/wheelbase)*rear_mu)
    rear_remaining=f32(1.-rear_transfer)
    front_transfer=(height/wheelbase)*front_mu
    front_remaining=1.-front_transfer
    if front_remaining==0 or rear_remaining==0:raise ValueError('nonzero brake transfer denominators required')
    numerator=(rear_mu*rear)/rear_remaining-(front_transfer/front_remaining)*((front_mu*height*mass_force)/wheelbase+front)*front_mu
    denominator=(front_mu*front)/front_remaining+(rear_transfer/rear_remaining)*(rear-(rear_mu*height*mass_force)/wheelbase)*rear_mu
    if denominator==0:raise ValueError('nonzero brake balance denominator required')
    return max(f32(.1),min(1.,f32((numerator/denominator)/ratio)))
