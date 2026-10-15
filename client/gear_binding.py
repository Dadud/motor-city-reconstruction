"""Original gear-table producers in 0x539fe0 and 0x53a538..0x53a5f6.

Inputs must come from the finalized component configuration. This does not
recover component loading, shift thresholds or complete owner initialization.
"""
from dataclasses import dataclass
import struct
from client.tire_response import f32


@dataclass(frozen=True)
class GearBinding:
    rpm_per_speed: tuple            # owner +0x1810
    speed_per_rpm: tuple            # owner +0x1830
    loss_final_ratio: tuple         # owner +0x1850
    wheel_inertia_factors: tuple    # owner +0x1870
    inverse_near_limit_speed: tuple # owner +0x17f0; maximum RPM minus 250
    final_drive_inertia: float      # owner +0x18b0


def bind_gear_tables(maximum_rpm,rear_width,rear_aspect,rear_rim,gear_ratios,
                     gear_losses,final_drive):
    if type(maximum_rpm) is not int or not -0x80000000<=maximum_rpm<=0x7fffffff:
        raise ValueError('int32 maximum RPM required')
    if len(gear_ratios)!=len(gear_losses) or not 0<=len(gear_ratios)<=8:
        raise ValueError('matching observed gear tables of at most eight entries required')
    width,aspect,rim,final=map(f32,(rear_width,rear_aspect,rear_rim,final_drive))
    ratios,losses=tuple(map(f32,gear_ratios)),tuple(map(f32,gear_losses))
    # Width mm, aspect percent and rim inches are converted by the original
    # constants. Keep both diameter terms unrounded until circumference store.
    circumference=f32(((width*f32(.001))*(aspect*f32(.01))*2.+rim*f32(.0254))*f32(3.1415927))
    revolutions=f32(maximum_rpm*f32(1./60.))
    rpm_per=[0.]*8
    for i,ratio in enumerate(ratios):
        denominator=final*ratio
        speed=0. if denominator==0 else f32(revolutions/denominator*circumference)
        rpm_per[i]=f32(maximum_rpm/speed) if abs(speed)>0 else 0.
    rpm_per[1]=0.  # Explicit final neutral-slot store in 0x539fe0.
    speed_per=[0.]*8;products=[0.]*8;inertia=[0.]*8;limit=[0.]*8
    shifted=(maximum_rpm-250+0x80000000)%0x100000000-0x80000000
    for i,(ratio,loss) in enumerate(zip(ratios,losses)):
        speed_per[i]=f32(1./rpm_per[i]) if rpm_per[i]!=0 else f32(.01)
        products[i]=f32(loss*final*ratio)
        if rpm_per[i]!=0:
            denominator=shifted*speed_per[i]
            if denominator==0:raise ValueError('nonzero near-limit speed denominator required')
            limit[i]=f32(1./denominator)
        inertia[i]=f32(ratio*f32(.0014241834))
    inertia[1]=0.  # Separate neutral override in the enclosing initializer.
    return GearBinding(tuple(rpm_per),tuple(speed_per),tuple(products),tuple(inertia),
                       tuple(limit),f32(final*f32(.0154740065)))


def bind_finalized_gear_tables(configuration,*,assembly_finalized):
    """Read the actual initializer offsets, refusing incomplete assembly input.

    The assertion records caller responsibility; it cannot certify provenance.
    """
    if assembly_finalized is not True:
        raise ValueError('complete component loading and assembly aggregation first')
    if len(configuration)!=0x820:raise ValueError('expected assembled 0x820-byte configuration')
    def integer(off):return struct.unpack_from('<i',configuration,off)[0]
    def number(off):return struct.unpack_from('<f',configuration,off)[0]
    count=integer(0x32c)
    if not 0<=count<=8:raise ValueError('gear count outside supported original table capacity')
    return bind_gear_tables(integer(0x70),number(0x228),number(0x22c),number(0x230),
        tuple(number(0x334+i*4) for i in range(count)),
        tuple(number(0x354+i*4) for i in range(count)),number(0x374))
