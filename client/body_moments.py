"""Full 0x540710 angular accumulation with original 0x540600 corrections."""
from dataclasses import dataclass
from client.tire_response import f32


@dataclass(frozen=True)
class MomentWheel:
    lateral_force: float
    longitudinal_force: float
    secondary_response: float
    support_correction: float
    contact: bool


@dataclass(frozen=True)
class BodyMomentState:
    wheels: tuple[MomentWheel,...]
    speed: float
    front_lever: float
    rear_lever: float
    front_track: float
    rear_track: float
    height_parameter: float
    mass_parameter: float
    inverse_pitch: float
    inverse_yaw: float
    inverse_roll: float
    pitch_multiplier: float
    front_vertical: float
    rear_vertical: float
    yaw_contribution: float
    alternate_mode: bool = False


def accumulate_body_moments(s: BodyMomentState):
    if len(s.wheels)!=4:
        raise ValueError('four consecutive wheel records required')
    speed,front,rear,ft,rt,height,mass,ip,iy,ir,pm,fv,rv,yc=map(f32,
        (s.speed,s.front_lever,s.rear_lever,s.front_track,s.rear_track,s.height_parameter,
         s.mass_parameter,s.inverse_pitch,s.inverse_yaw,s.inverse_roll,s.pitch_multiplier,
         s.front_vertical,s.rear_vertical,s.yaw_contribution))
    wheels=[]
    for w in s.wheels:
        if type(w.contact) is not bool:
            raise ValueError('boolean contact required')
        wheels.append(MomentWheel(*map(f32,(w.lateral_force,w.longitudinal_force,
                                           w.secondary_response,w.support_correction)),w.contact))
    k=f32(.15915494)
    ft,rt=f32(ft*.5),f32(rt*.5)
    height=f32(height*f32(.9090909))
    lateral=f32(((wheels[0].lateral_force+wheels[1].lateral_force)*front
                 -(wheels[3].lateral_force+wheels[2].lateral_force)*rear)*k)
    extra=f32(front*.25*yc*k)
    torque=0.0 if s.alternate_mode else ((wheels[0].longitudinal_force-wheels[1].longitudinal_force)*ft
        +(wheels[3].longitudinal_force-wheels[2].longitudinal_force)*rt)*k
    yaw=f32((torque+extra+lateral)*iy)
    yaw=f32(sum(w.secondary_response for w in wheels)*iy*k+yaw)
    if abs(speed)<.5:
        return 0.0,yaw,0.0
    pitch,roll=0.0,0.0
    # The original cross-product order is force x position. Rear records are
    # consumed in 3,2 order, unlike the consecutive-record interface.
    for i,x,z,v in ((0,-ft,front,fv),(1,ft,front,fv),(3,-rt,-rear,rv),(2,rt,-rear,rv)):
        w=wheels[i]
        pitch=f32(pitch+f32(v*z-w.longitudinal_force*height))
        roll=f32(roll+f32(w.lateral_force*height-v*x))
    pitch=f32(pitch*ip*pm*k)
    roll=f32(roll*ir*k)
    # Correction helper retains extended products except the quarter-mass
    # wheel product and the final accumulator stores.
    quarter=f32(mass*.25)
    for i,w in enumerate(wheels):
        if w.contact and w.support_correction!=0:
            contribution=f32(quarter*w.support_correction)
            pitch=f32(pitch+contribution*(front if i<2 else rear)*ip*k)
            roll=f32(roll+contribution*(ft if i<2 else rt)*ir*k)
    return pitch,yaw,roll
