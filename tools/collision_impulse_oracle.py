"""Full original collision impulse and plane-height helpers in bounded CPU execution."""
import argparse
import itertools
import json
import struct
from client.collision_impulse import CollisionInertia, impulse_motion, plane_height
from tools.native_oracle import DynoOracle

IDENTITY=(1,0,0,0,1,0,0,0,1)
ROTATED=(0,0,-1,0,1,0,1,0,0)
INVERSE=(0,0,1,0,1,0,-1,0,0)


class CollisionImpulseOracle(DynoOracle):
    def motion(self, body, impulse, lever, radial):
        self._reset()
        owner=self.inputs; a,b,c,out1,out2=(self.inputs+i for i in (0x400,0x420,0x440,0x460,0x480))
        image=bytearray([0xa5]*0x320)
        struct.pack_into('<f',image,0x54,body.inverse_mass)
        struct.pack_into('<9f',image,0x78,*body.body_to_world)
        struct.pack_into('<9f',image,0x9c,*body.world_to_body)
        struct.pack_into('<3f',image,0x2fc,*body.inverse_inertia)
        self.cpu.mem_write(owner,bytes(image))
        for p,v in ((a,impulse),(b,lever),(c,radial)):
            self.cpu.mem_write(p,struct.pack('<3f',*v))
        self.cpu.mem_write(out1,bytes([0xa5])*44)
        self.cpu.mem_write(self.frame-0x1000,struct.pack('<7I',self.stop,owner,a,b,c,out1,out2))
        self._run(0x457780,self.stop,count=1000)
        if bytes(self.cpu.mem_read(owner,len(image)))!=image: raise AssertionError('original impulse helper changed body')
        for p,v in ((a,impulse),(b,lever),(c,radial)):
            if bytes(self.cpu.mem_read(p,12))!=struct.pack('<3f',*v): raise AssertionError('original impulse helper changed input')
        return (struct.unpack('<3f',self.cpu.mem_read(out1,12)),
                struct.unpack('<3f',self.cpu.mem_read(out2,12)))

    def height(self,normal,point,query):
        self._reset()
        a,b,c,out=(self.inputs+i for i in (0,32,64,96))
        for p,v in ((a,normal),(b,point),(c,query)):self.cpu.mem_write(p,struct.pack('<3f',*v))
        # Fixed wrapper stores the x87 return once, exactly as a float caller does.
        entry=self.stub+0x100
        code=b'\x68'+struct.pack('<I',c)+b'\x68'+struct.pack('<I',b)+b'\x68'+struct.pack('<I',a)
        call_end=entry+len(code)+5
        code+=b'\xe8'+struct.pack('<i',0x4b71a0-call_end)+b'\x83\xc4\x0c'
        code+=b'\xd9\x1d'+struct.pack('<I',out)+b'\xc3'
        self.cpu.mem_write(entry,code)
        self.cpu.mem_write(self.frame-0x1000,struct.pack('<I',self.stop))
        self._run(entry,self.stop,count=100)
        return struct.unpack('<f',self.cpu.mem_read(out,4))[0]


def impulse_cases():
    bodies=(CollisionInertia(m,i,w,b) for m,i,(w,b) in itertools.product(
        (0,0.0005,0.25,1),((0,0,0),(0.01,0.02,0.03),(1,2,3)),
        ((IDENTITY,IDENTITY),(INVERSE,ROTATED))))
    for body in bodies:
        for p,l,r in itertools.product(((0,0,0),(0,-1,0),(2,-3,4),(-1,2,-4),(100,-300,250)),
            ((0,0,0),(1,0,0),(0,2,1),(-0.25,0.1,0.8)),
            ((0,1,0),(0,-1,0),(0.6,0.8,0),(0,0,0))):yield body,p,l,r


def height_cases():
    yield from itertools.product(((0,1,0),(0,-1,0),(0.5,0.75,0.25),(-2,0.125,3)),
        ((0,0,0),(10,20,-5),(-1.25,0.2,30)),
        ((0,0,0),(10,99,-5),(-1000,12,250),(0.125,-4,0.25)))


def compare(executable):
    oracle=CollisionImpulseOracle(executable);count=0;maximum=0.0
    for body,p,l,r in impulse_cases():
        linear,angular=oracle.motion(body,p,l,r);expected=impulse_motion(body,p,l,r)
        for actual,want in zip((*linear,*angular),(*expected.linear,*expected.angular)):
            maximum=max(maximum,abs(actual-want))
            if actual!=want:raise AssertionError((body,p,l,r,linear,angular,expected))
        count+=1
    heights=0
    for n,p,q in height_cases():
        actual=oracle.height(n,p,q);expected=plane_height(n,p,q)
        if actual!=expected:raise AssertionError((n,p,q,actual,expected))
        heights+=1
    return {'impulse_cases':count,'plane_height_cases':heights,'maximum_error':maximum,
            'scope':'complete 0x457780 and float-stored 0x4b71a0; supplied body/contact data'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable')
    print(json.dumps(compare(p.parse_args().executable)))
