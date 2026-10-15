"""Recovered mechanical component loaders; no inferred fallback for unknowns."""
from dataclasses import dataclass
import math
import struct
from client.tire_response import f32


@dataclass(frozen=True)
class ComponentLoadResult:
    status: int
    configuration: bytes
    component: bytes


def _truncated_word(value):
    value=math.trunc(value)
    if not -0x8000000000000000<=value<=0x7fffffffffffffff:value=-0x8000000000000000
    return ((value+0x80000000)&0xffffffff)-0x80000000


def load_engine_block(configuration,component):
    """Complete 0x54a5a0 with validator 0x542ef0 and material quality.

    Finite numeric observations and bounded strings are authored boundaries.
    Native status 1 means count mismatch; status 2 means invalid record. Failure
    preserves both inputs. RPM placeholders match the original loader and must
    still be replaced by engine-curve finalization before authentic driving.
    """
    if len(configuration)!=0x820 or len(component)!=0x984:
        raise ValueError('expected mechanical configuration and component images')
    configuration=bytes(configuration);component=bytes(component)
    def failure(status):return ComponentLoadResult(status,configuration,component)
    if struct.unpack_from('<I',component,0x14)[0]&0x3fffffff!=7:return failure(1)
    def number(offset):return struct.unpack_from('<f',component,offset)[0]
    mass=number(0x30);duty=number(0x34)
    bore,stroke,displacement,cylinders,unused,material,last=tuple(number(0x3c+i*4) for i in range(7))
    if not all(math.isfinite(v) for v in (mass,duty,bore,stroke,displacement,cylinders,unused,material,last)):
        return failure(2)
    family=struct.unpack_from('<I',component,0x53b)[0]
    if not (f32(30)<=mass<=f32(200) and f32(.0508)<=bore<=f32(.127) and
            f32(.0635)<=stroke<=f32(.127) and f32(3)<=displacement<=f32(10) and
            f32(5)<=last<=f32(40) and 6<=round(cylinders)<=8 and 1<=family<=26 and
            0<=round(material)<=9 and _truncated_word(material) not in (4,5,6,7,9)):
        return failure(2)
    strings=[]
    for index in range(6):
        value=component[0x120+index*32:0x140+index*32]
        if b'\0' not in value:raise ValueError('engine block text requires a bounded terminator')
        strings.append(value.split(b'\0',1)[0]+b'\0')
    out=bytearray(configuration);part=bytearray(component)
    def put(offset,value):struct.pack_into('<f',out,offset,value)
    def integer(offset,value):struct.pack_into('<i',out,offset,value)
    existing=struct.unpack_from('<f',out,0x20)[0]
    if not math.isfinite(existing):raise ValueError('finite mass accumulator required')
    put(0x20,existing+mass)
    for destination,source in ((0x428,0x30),(0x430,0x3c),(0x434,0x40),
                               (0x438,0x44),(0x440,0x53b),(0x44c,0x54)):
        out[destination:destination+4]=component[source:source+4]
    integer(0x42c,_truncated_word(duty));integer(0x43c,_truncated_word(cylinders))
    selector=_truncated_word(material);integer(0x444,selector)
    for destination,value in zip((0x450,0x459,0x45d,0x461,0x465,0x469),strings):
        out[destination:destination+len(value)]=value
    out[0x7c:0x80]=out[0x43c:0x440];out[0x74:0x78]=out[0x438:0x43c]
    integer(0x6c,500);integer(0x70,7000);put(0x448,1.)
    out[0x80:0xe4]=bytes(100)
    quality=(1.,1.05,.96,.97,1.1,1.4,1.75,2.)[selector] if 0<=selector<=7 else 1.
    struct.pack_into('<f',part,0x1c,quality)
    return ComponentLoadResult(0,bytes(out),bytes(part))


def _nearest_word(value):
    value=round(value)
    return value if -0x80000000<=value<=0x7fffffff else -0x80000000


class _Image:
    def __init__(self,configuration,component):
        if len(configuration)!=0x820 or len(component)!=0x984:
            raise ValueError('expected mechanical configuration and component images')
        self.initial=bytes(configuration);self.source=bytes(component)
        self.out=bytearray(configuration);self.part=bytearray(component)

    def result(self,status):
        return ComponentLoadResult(status,bytes(self.out),bytes(self.part))

    def fail(self,status):return ComponentLoadResult(status,self.initial,self.source)

    def count(self):return struct.unpack_from('<I',self.part,0x14)[0]&0x3fffffff

    def number(self,offset):
        value=struct.unpack_from('<f',self.part,offset)[0]
        if not math.isfinite(value):raise ValueError('finite mechanical observation required')
        return value

    def existing(self,offset):
        value=struct.unpack_from('<f',self.out,offset)[0]
        if not math.isfinite(value):raise ValueError('finite configuration observation required')
        return value

    def put(self,offset,value):struct.pack_into('<f',self.out,offset,value)

    def integer(self,offset,value):struct.pack_into('<i',self.out,offset,value)

    def copy(self,destination,source,size=4):self.out[destination:destination+size]=self.part[source:source+size]

    def nearest(self,offset):return _nearest_word(self.number(offset))

    def trunc(self,offset):return _truncated_word(self.number(offset))

    def bounded(self,offset,low,high):return f32(low)<=self.number(offset)<=f32(high)

    def rounded_between(self,offset,low,high):return low<=self.nearest(offset)<=high

    def add_mass(self,unsprung=None):
        mass=self.number(0x30);self.put(0x20,self.existing(0x20)+mass)
        if unsprung is not None:self.put(0x28,self.existing(0x28)+mass*unsprung)

    def front(self):return struct.unpack_from('<i',self.part,0x18)[0] in (1,2)

    def quality(self):
        duty=self.nearest(0x34)
        struct.pack_into('<f',self.part,0x1c,.75 if duty==0 else 2. if duty==2 else 4. if duty==3 else 1.)


def load_transmission(configuration,component):
    """Complete 0x54d080 / 0x543e90, including original gear-table copies."""
    m=_Image(configuration,component)
    if m.count()!=19:return m.fail(1)
    ratios=tuple(m.number(0x48+i*4) for i in range(8))
    losses=tuple(m.number(0x68+i*4) for i in range(8))
    valid=(m.bounded(0x30,20,100) and m.rounded_between(0x3c,0,1) and
        m.rounded_between(0x44,4,64) and m.rounded_between(0x40,4,8) and
        all(v<5 for v in ratios) and all(v<=1 for v in losses) and
        1+sum(v!=0 for v in ratios)==m.trunc(0x40) and m.rounded_between(0x34,0,3))
    if not valid:return m.fail(2)
    m.add_mass();m.copy(0x680,0x30)
    for destination,source in ((0x684,0x34),(0x68c,0x3c),(0x690,0x40),(0x694,0x44),
                               (0x32c,0x40),(0x330,0x44)):
        m.integer(destination,m.nearest(source))
    m.put(0x688,(m.nearest(0x34)+1)*250.)
    for destination,source in ((0x698,0x48),(0x6b8,0x68),(0x334,0x48),(0x354,0x68)):
        m.copy(destination,source,32)
    m.quality();return m.result(0)


def load_rear_end(configuration,component):
    """Complete 0x54d2f0 / 0x543fc0, including final-drive producer."""
    m=_Image(configuration,component)
    if m.count()!=3:return m.fail(1)
    if not (m.bounded(0x30,18,50) and m.rounded_between(0x40,0,1) and
            m.bounded(0x3c,2.5,6) and m.bounded(0x44,.9,1) and m.rounded_between(0x34,0,3)):
        return m.fail(2)
    m.add_mass();m.copy(0x6d8,0x30);m.copy(0x6e4,0x3c);m.copy(0x6e8,0x44);m.copy(0x374,0x3c)
    m.integer(0x6ec,m.nearest(0x40));m.integer(0x6dc,m.nearest(0x34))
    duty=m.nearest(0x34)+1;m.put(0x6e0,duty*duty*100.+650.)
    m.quality();return m.result(0)


def load_wheel_rim(configuration,component):
    """Complete 0x54d420 / 0x5440a0; unusual attachments take rear branch."""
    m=_Image(configuration,component)
    if m.count()!=1:return m.fail(1)
    if not (m.bounded(0x30,5,75) and m.rounded_between(0x3c,0,9) and m.trunc(0x3c)!=9):
        return m.fail(2)
    m.add_mass(1.);base=0x700 if m.front() else 0x70c
    m.copy(base,0x30);m.integer(base+4,m.nearest(0x34));m.integer(base+8,m.nearest(0x3c))
    m.quality();return m.result(0)


def load_spring(configuration,component):
    """Complete 0x54a840 / 0x543070, including once-per-axle roll stores."""
    m=_Image(configuration,component)
    if m.count()!=2:return m.fail(1)
    if not (m.bounded(0x30,2,30) and m.bounded(0x3c,10000,120000) and
            m.rounded_between(0x34,0,3) and m.rounded_between(0x40,0,3)):
        return m.fail(2)
    m.add_mass(.5);base=0x628 if m.front() else 0x638
    m.copy(base,0x30);m.integer(base+4,m.trunc(0x34))
    m.copy(base+8,0x3c);m.integer(base+12,m.trunc(0x40))
    attachment=struct.unpack_from('<i',component,0x18)[0]
    if attachment in (1,3):
        track,scale,target=(0x30,.76,0xfc) if attachment==1 else (0x34,.68,0x104)
        arm=m.existing(track)*f32(scale)
        m.put(target,((arm*m.number(0x3c))*arm)*f32(.0087265)+m.existing(target))
    return m.result(0)


def load_shock(configuration,component):
    """Complete 0x54a9a0 / 0x543120 with original half-mass accumulator."""
    m=_Image(configuration,component)
    if m.count()!=2:return m.fail(1)
    if not (m.bounded(0x30,2,10) and m.rounded_between(0x34,0,3) and
            m.bounded(0x3c,.2,.4) and m.bounded(0x40,.1016,.4064)):
        return m.fail(2)
    m.add_mass(.5);base=0x608 if m.front() else 0x618
    m.copy(base,0x30);m.integer(base+4,m.trunc(0x34))
    m.copy(base+8,0x3c);m.copy(base+12,0x40)
    m.quality();return m.result(0)


def load_brake(configuration,component):
    """Complete 0x54ab30 / 0x5431e0; each brake adds at least four mass units."""
    m=_Image(configuration,component)
    if m.count()!=5:return m.fail(1)
    if not (m.bounded(0x30,2,20) and m.rounded_between(0x3c,0,1) and
            m.rounded_between(0x40,0,3) and m.rounded_between(0x44,0,20) and
            m.bounded(0x48,.0254,.1016) and m.rounded_between(0x4c,0,1) and
            m.rounded_between(0x34,0,3)):
        return m.fail(2)
    mass=max(4.,m.number(0x30))
    m.put(0x20,m.existing(0x20)+mass);m.put(0x28,m.existing(0x28)+mass)
    base=0x5c8 if m.front() else 0x5e8
    m.copy(base,0x30)
    for destination,source in ((base+4,0x34),(base+8,0x3c),(base+12,0x40),
                               (base+16,0x44),(base+24,0x4c)):
        m.integer(destination,m.trunc(source))
    m.copy(base+20,0x48)
    material=m.trunc(0x40)
    m.put(base+28,{1:300.,2:375.,3:450.}.get(material,225.))
    struct.pack_into('<f',m.part,0x1c,{0:.8,2:1.5,3:2.}.get(material,1.))
    return m.result(0)


def _same_engine_family(m):
    family=struct.unpack_from('<I',m.part,0x53b)[0]
    return family!=0 and family==struct.unpack_from('<I',m.out,0x440)[0]


def _material_quality(m,offset,head=False):
    table=(1.,1.05,.96,.97,1.1,1.4,1.75,2.) if head else (1.,1.04,.95,.96,1.2,1.5,1.65,3.,.93)
    index=m.nearest(offset)
    struct.pack_into('<f',m.part,0x1c,table[index] if 0<=index<len(table) else 1.)


def _cylinder_mass(m,individual,total):
    # FST records the rounded product but leaves the extended product on the
    # x87 stack for addition to the total. Do not add the rounded field back.
    count=struct.unpack_from('<i',m.out,0x43c)[0]
    product=count*m.number(0x30)
    m.copy(individual,0x30);m.put(total,product)
    m.put(0x20,m.existing(0x20)+product)


def load_cylinder_head(configuration,component):
    """Complete 0x54bd70, including family validation and compression base."""
    m=_Image(configuration,component)
    if m.count()!=7:return m.fail(1)
    if not (_same_engine_family(m) and m.bounded(0x30,10,80) and
            m.rounded_between(0x3c,0,2) and m.rounded_between(0x40,0,9) and
            m.trunc(0x40) not in (8,9) and m.rounded_between(0x44,0,5) and
            m.bounded(0x48,.97,1.03) and m.bounded(0x4c,6,20) and
            m.bounded(0x50,25.4,63.5) and m.bounded(0x54,25.4,50.8) and
            struct.unpack_from('<I',m.part,0x53b)[0]<=26):return m.fail(2)
    m.add_mass()
    for destination,source in ((0x504,0x30),(0x518,0x48),(0x51c,0x4c),
            (0x54,0x4c),(0x520,0x53b),(0x524,0x50),(0x528,0x54)):
        m.copy(destination,source)
    for destination,source in ((0x508,0x34),(0x50c,0x3c),(0x510,0x44),(0x514,0x40)):
        m.integer(destination,m.nearest(source))
    _material_quality(m,0x40,head=True)
    return m.result(0)


def load_camshaft(configuration,component):
    """Complete 0x54bef0 / 0x544710 with the original material selectors."""
    m=_Image(configuration,component)
    if m.count()!=9:return m.fail(1)
    if not (_same_engine_family(m) and m.bounded(0x30,5,25) and
            m.bounded(0x48,5,20) and m.bounded(0x4c,5,20) and
            m.rounded_between(0x3c,0,2) and m.rounded_between(0x40,0,9) and
            m.trunc(0x40) not in (8,9) and m.bounded(0x44,.9,1.1)):return m.fail(2)
    m.add_mass();m.copy(0x52c,0x30);m.copy(0x53c,0x44);m.copy(0x540,0x53b)
    for destination,source in ((0x530,0x34),(0x534,0x3c),(0x538,0x40)):
        m.integer(destination,m.nearest(source))
    m.copy(0x544,0x48,24);_material_quality(m,0x40)
    return m.result(0)


def load_valve_train(configuration,component):
    """Complete 0x54c090; final value uses CRT truncation, not rounding."""
    m=_Image(configuration,component)
    if m.count()!=3:return m.fail(1)
    if not (_same_engine_family(m) and m.bounded(0x30,5,30) and
            m.rounded_between(0x3c,0,2) and m.bounded(0x40,.9,1.1)):return m.fail(2)
    m.add_mass();m.copy(0x55c,0x30);m.copy(0x568,0x40);m.copy(0x56c,0x53b)
    m.integer(0x560,m.nearest(0x34));m.integer(0x564,m.nearest(0x3c))
    m.integer(0x570,m.trunc(0x44));m.quality()
    return m.result(0)


def load_crankshaft(configuration,component):
    """Complete 0x54bac0; semantic rejection retains configuration writes."""
    m=_Image(configuration,component)
    if m.count()!=2:return m.fail(1)
    m.add_mass();m.copy(0x490,0x30);m.copy(0x49c,0x53b);m.copy(0x4a0,0x40)
    m.integer(0x494,m.nearest(0x34));m.integer(0x498,m.nearest(0x3c))
    if not (_same_engine_family(m) and m.bounded(0x30,15,50) and
            m.rounded_between(0x34,0,3) and m.rounded_between(0x3c,0,9) and
            m.nearest(0x3c) not in (2,3,9)):return m.result(2)
    _material_quality(m,0x3c)
    return m.result(0)


def load_connecting_rods(configuration,component):
    """Complete 0x54bc10; one mass per cylinder, writes precede validation."""
    m=_Image(configuration,component)
    if m.count()!=3:return m.fail(1)
    _cylinder_mass(m,0x4a4,0x4ac)
    m.integer(0x4a8,m.nearest(0x34));m.integer(0x4b0,m.nearest(0x3c))
    for destination,source in ((0x4b4,0x53b),(0x4b8,0x40),(0x4bc,0x44)):
        m.copy(destination,source)
    if not (_same_engine_family(m) and m.bounded(0x30,.1,2) and
            m.rounded_between(0x34,0,3) and m.rounded_between(0x3c,0,9) and
            m.trunc(0x3c) not in (8,9) and m.bounded(0x40,30,250)):return m.result(2)
    _material_quality(m,0x3c)
    return m.result(0)


def load_pistons(configuration,component):
    """Complete 0x54b940; piston contribution adds to head compression base."""
    m=_Image(configuration,component)
    if m.count()!=4:return m.fail(1)
    if not (_same_engine_family(m) and m.bounded(0x30,.1,2) and
            m.rounded_between(0x3c,0,3) and m.rounded_between(0x40,0,9) and
            m.bounded(0x44,-1,4) and m.trunc(0x40) not in (8,9)):return m.fail(2)
    _cylinder_mass(m,0x470,0x478)
    for destination,source in ((0x474,0x34),(0x47c,0x3c),(0x480,0x40)):
        m.integer(destination,m.nearest(source))
    for destination,source in ((0x484,0x44),(0x488,0x53b),(0x48c,0x48)):
        m.copy(destination,source)
    m.put(0x54,m.existing(0x54)+m.number(0x44));_material_quality(m,0x40)
    return m.result(0)


def load_tire(configuration,component,templates=None):
    """Complete 0x54e170 with external auxiliary table; rejection can mutate.

    Missing templates reproduce service-unavailable status 4. The original has
    no safe index check; the authored adapter bounds indices to allocated slots.
    """
    m=_Image(configuration,component)
    if templates is None:return m.fail(4)
    if len(templates)!=0x1d68:raise ValueError('expected tire auxiliary image')
    if m.count()!=4:return m.fail(1)
    if not (m.bounded(0x3c,100,500) and m.bounded(0x40,25,95) and
            m.bounded(0x44,12,25) and m.bounded(0x30,8,30) and
            m.rounded_between(0x34,0,3)):return m.fail(2)
    index=m.trunc(0x48)
    if not 0<=index<20:raise ValueError('tire template index outside original allocation')
    base=index*0x178
    def template(offset):
        value=struct.unpack_from('<f',templates,base+offset)[0]
        if not math.isfinite(value):raise ValueError('finite tire template observation required')
        return value
    m.add_mass(1.)
    width=m.number(0x3c)
    if width>215:
        increment=min(f32(.005),max(0.,f32((width-215)*f32(.00004))))
        m.put(0,m.existing(0)+increment)
    shift=0 if m.front() else 0x104
    m.copy(0x220+shift,0x30);m.integer(0x224+shift,m.trunc(0x34))
    for destination,source in ((0x124,0x3c),(0x128,0x40),(0x12c,0x44)):
        m.copy(destination+shift,source)
    m.put(0x138+shift,0.)
    m.out[0x150+shift:0x220+shift]=bytes(0xd0)
    for destination,source in ((0x134,8),(0x130,12),(0x140,0x170),
            (0x13c,0x168),(0x144,0x178),(0x148,0x174)):
        m.put(destination+shift,template(source))
    m.put(0x14c+shift,template(0x16c)*f32(.01))
    m.out[0x154+shift:0x1b8+shift]=templates[base+0xa0:base+0x104]
    m.out[0x1bc+shift:0x220+shift]=templates[base+0x104:base+0x168]
    struct.pack_into('<f',m.part,0x1c,.96 if m.number(0x48)==4. else 1.)
    valid=(f32(.7)<=m.existing(0x140+shift)<=2 and
        127<=m.existing(0x144+shift)<=508)
    return m.result(0 if valid else 2)


MECHANICAL_LOADERS={160001:load_engine_block,130001:load_transmission,
    140001:load_rear_end,100001:load_wheel_rim,12001:load_spring,
    11001:load_shock,10001:load_brake,1000001:load_cylinder_head,
    1100001:load_camshaft,1200001:load_valve_train,180001:load_crankshaft,
    190001:load_connecting_rods,200001:load_pistons,110001:load_tire}
