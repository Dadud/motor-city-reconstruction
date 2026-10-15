"""Recovered 0x43a990 body-construction phase before 0x53a1f0.

Model assembly and prior high-offset owner geometry are required caller inputs.
This phase does not run the main owner initializer or final wheel setup.
"""
import struct
from client.body_constructor import construct_body
from client.body_geometry import customize_body_samples
from client.owner_binding import bind_startup_com
from client.owner_wheel_setup import adjust_owner_stance


def prepare_startup_body(owner,configuration,half_extents,identity,*,assembly_finalized):
    if assembly_finalized is not True or len(configuration)!=0x820:
        raise ValueError('finalized mechanical configuration required')
    def number(offset): return struct.unpack_from('<f',configuration,offset)[0]
    selector=struct.unpack_from('<i',configuration,0x48)[0]
    out=bytearray(construct_body(owner,identity,number(0x20),half_extents,0,0))
    out[6]=1;struct.pack_into('<f',out,0x318,.65)
    points=struct.unpack_from('<66f',out,0xe0)
    points=customize_body_samples(selector,tuple(tuple(points[i:i+3]) for i in range(0,66,3)))
    struct.pack_into('<66f',out,0xe0,*(v for p in points for v in p))
    out=bytearray(adjust_owner_stance(out))
    responses={0:(.9,1.,.95),1:(.8,1.,.95),2:(.8,1.,.8),3:(.8,1.,.8),
               4:(.8,1.,.8),5:(.8,1.,.8),6:(.9,1.,.8),7:(.9,1.,.95)}
    struct.pack_into('<3f',out,0x30c,*responses[selector])
    out[0x308:0x30c]=configuration[:4]
    com=bind_startup_com(number(0x38),struct.unpack_from('<f',out,0xd0)[0],
        struct.unpack_from('<f',out,0x18c4)[0],struct.unpack_from('<f',out,0x18b8)[0])
    struct.pack_into('<2f',out,0x60,com.vertical,com.longitudinal)
    return bytes(out)
