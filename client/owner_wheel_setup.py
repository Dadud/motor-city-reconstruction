"""Recovered complete 0x53b8a0 wheel setup and 0x53b3c0 stance adjustment.

Inputs are finalized mechanical configuration and explicit prior owner state.
This does not supply model extents, projected area, or the main owner initializer.
"""
import math
import struct
from client.tire_response import f32

OWNER_SIZE=0x2000


def _number(image,offset):
    value=struct.unpack_from('<f',image,offset)[0]
    if not math.isfinite(value):raise ValueError('finite startup observations required')
    return value


def _stance(front,rear):
    front=f32(front+max(0.,f32(front-f32(.37))))
    rear=f32(rear+max(0.,f32(rear-f32(.37))))
    return min(0.,f32(front-rear)),min(0.,f32(rear-front))


def adjust_owner_stance(owner):
    """Complete original 0x53b3c0, preserving all other owner bytes."""
    if len(owner)!=OWNER_SIZE:raise ValueError('expected complete owner image')
    out=bytearray(owner)
    n=lambda offset:_number(out,offset)
    def put(offset,value):struct.pack_into('<f',out,offset,value)
    front,rear=_stance(n(0x18ec),n(0x18f0));middle=(front+rear)*f32(.5)
    for offsets,delta in (((0xe4,0xf0,0x1bc),front),((0xfc,0x108,0x1e0),rear),
                           ((0x1c8,0x180,0x1d4),middle)):
        for offset in offsets:put(offset,n(offset)-delta)
    for offset in (0x1c0,0xe8,0xf4):put(offset,n(0x18c4)+n(0x18ec))
    for offset in (0x100,0x10c,0x1e4):put(offset,n(0x18c8)-n(0x18f0))
    return bytes(out)


def initialize_owner_wheels(owner,configuration,*,assembly_finalized):
    """Complete original 0x53b8a0 including the real stance helper.

    Original oddities are retained: rear width scale divides by the front
    template width, and all-zero steering flags enable the rear pair.
    """
    if assembly_finalized is not True:raise ValueError('complete mechanical assembly first')
    if len(owner)!=OWNER_SIZE or len(configuration)!=0x820:raise ValueError('expected owner and configuration images')
    out=bytearray(owner)
    n=lambda offset:_number(out,offset)
    c=lambda offset:_number(configuration,offset)
    def put(offset,value):struct.pack_into('<f',out,offset,value)
    def copy(destination,source):out[destination:destination+4]=configuration[source:source+4]
    radii=(n(0x18ec),n(0x18f0))
    if min(radii)<=0 or c(0x144)<=0:raise ValueError('positive axle radii and front template width required')
    for offset,value in ((0x6b8,radii[0]),(0x7c4,radii[0]),(0x8d0,radii[1]),(0x9dc,radii[1])):put(offset,value)
    mass_available=struct.unpack_from('<I',out,0x490)[0]!=0 and all(c(o)!=0 for o in (0x700,0x70c,0x220,0x324))
    for wheel in range(4):
        base=0x6b4+wheel*0x10c;front=wheel<2
        copy(base,0x11c if front else 0x120)
        put(base-0x5c,1.);put(base-0x58,1.);put(base+0x1c,c(0x20)*f32(.25))
        out[base+0x34]=1
        for relative in (-0xb8,0x18,0x20,0x24,0x28,0x2c,-0x4c,-0x40,-0x3c,-0x38,-0x34,-0x30,-0x2c,-0x28):put(base+relative,0.)
        mass=(c(0x220)+c(0x700) if front else c(0x324)+c(0x70c)) if mass_available else 15.
        radius=n(base+4);spin=f32(radius*radius*mass*f32(.5))
        if spin<=0:raise ValueError('positive wheel inertia required')
        put(base-0x24,spin)
        width=c(0x124 if front else 0x228)*f32(.001)
        copy(base+0x14,0x134 if front else 0x238)
        transverse=width*width*f32(.083333336)+spin
        put(base-0x1c,transverse);put(base-0x20,transverse)
        put(base-0x18,1./spin);put(base-0x14,1./transverse);put(base-0x10,1./transverse)
        ratio=f32(width/(c(0x144)*f32(.001)))
        put(base+0x40,min(f32(1.5),max(f32(.9),ratio)))
    for index,destination in enumerate((0x6c1,0x7cd,0x8d9,0x9e5)):out[destination]=configuration[0x60+index]
    if sum(configuration[0x60:0x64])==0:out[0x8d9]=out[0x9e5]=1
    for offset,source in ((0x604,0x138),(0x710,0x138),(0x928,0x23c),(0x81c,0x23c)):
        put(offset,c(source)*f32(.0055555557))
    for destination,source in ((0x7d4,0x134),(0x6c8,0x134),(0x8e0,0x238),(0x9ec,0x238),
            (0x6f8,0x140),(0x804,0x140),(0xa1c,0x244),(0x910,0x244),
            (0x6c4,0x130),(0x7d0,0x130),(0x9e8,0x234),(0x8dc,0x234)):
        copy(destination,source)
    bias=f32(c(0x58)*f32(.5))
    for offset in (0x6a8,0x7b4):put(offset,bias)
    for offset in (0x9cc,0x8c0):put(offset,f32(.5)-bias)
    out[0x6c0]=out[0x7cc]=1;out[0x9e4]=out[0x8d8]=int(configuration[0xe4]!=0)
    for offset,source in ((0x6bc,0x224),(0x7c8,0x224),(0x9e0,0x328),(0x8d4,0x328)):
        selector=struct.unpack_from('<i',configuration,source)[0]
        put(offset,{0:160.,2:240.,3:300.}.get(selector,190.)*f32(.27778))
    front,rear=_stance(*radii)
    fx=c(0x30)*f32(.5);rx=c(0x34)*f32(.5)
    for offset,value in ((0x6fc,-fx),(0x808,fx),(0x914,rx),(0xa20,-rx),
        (0x700,-(front+n(0xd0))),(0x80c,-(front+n(0xd0))),
        (0x918,-(rear+n(0xd0))),(0xa24,-(rear+n(0xd0))),
        (0x704,n(0x18c4)),(0x810,n(0x18c4)),(0x91c,n(0x18c8)),(0xa28,n(0x18c8))):put(offset,value)
    return adjust_owner_stance(out)
