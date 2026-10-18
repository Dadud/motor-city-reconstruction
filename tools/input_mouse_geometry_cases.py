"""Original bounds/position execution with explicit context/cursor/lock bridges.

This is CPU-only instruction execution, not Windows or mouse hardware behavior.
"""
import struct
from tools.mouse_input_cases import (GLOBALS,SIZE,MOUSE,ENTER,LEAVE,NOTIFY_A,NOTIFY_B,
                                    CONVERT,POSITION,CURSOR,fixtures)
QUERY,CTOR,CONTEXT,DTOR=0x6be930,0x7b54a0,0x6cf1b0,0x7b54d0
GATE=0x7000ee00

def rows():
    # Reuse adversarial cursor cases and their complete window/mouse images.
    base=list(fixtures(1))
    for operation in (0,1):
        for index,row in enumerate(base):
            mask,value,success,cx,cy,enabled,callback,*rest=row
            args=rest[:6];globals=rest[6:6+SIZE];image=rest[6+SIZE:]
            maxx,maxy,miny,minx,buttons,y,x=struct.unpack('<7I',bytes(image))
            if operation==0:
                # Setter bounds differ from original bounds, and its child must
                # use cached coordinates/buttons rather than invented inputs.
                arguments=[minx,miny,maxx,maxy]
                image=list(struct.pack('<7I',123,456,0,0,buttons,args[1],args[0]))
                queries=((0,0),)
            else:
                arguments=[args[0],args[1],0,0]
                queries=((0,0),(0,1),(1,0),(1,1))
            for first,second in queries:
                yield [operation,first,second,mask,value,success,cx,cy,enabled,callback,
                       0x11223344,0x55667788,*arguments,*globals,*image]

def capture(oracle):
    from unicorn import UC_HOOK_CODE
    cpu=oracle.cpu;logs=[];script={}
    def read(a):return struct.unpack('<I',cpu.mem_read(a,4))[0]
    def put(a,v):cpu.mem_write(a,struct.pack('<I',v&0xffffffff))
    def log(kind,a=0,b=0,c=0,d=0):
        logs.append([kind,a,b,c,d,read(0x8c45fc),read(0x8c4714),read(0xacae14),read(0xacadb0),
                     *struct.unpack('<7I',cpu.mem_read(MOUSE,28))])
    def observe(cpu,address,size,user):
        stack=cpu.reg_read(oracle.reg.UC_X86_REG_ESP)+4
        mask,value=script['mask'],script['value']
        if address in (QUERY,CTOR,CONTEXT,DTOR,GATE):
            identity=0x8c4938 if address==GATE else address
            argument=read(stack) if address in (QUERY,GATE) else 0
            log(9,identity,argument,read(0x8c4600),read(0x8c4604))
            if address==QUERY:
                cpu.reg_write(oracle.reg.UC_X86_REG_EAX,script['queries'][script['query_count']])
                script['query_count']+=1
            return
        if address in (ENTER,LEAVE):
            log(1 if address==ENTER else 2,read(stack))
            if address==ENTER:
                if mask&1:
                    put(0x8c45fc,0)
                    for offset in (0,4,8,12):put(MOUSE+offset,0x7fffffff)
                if mask&2:put(0xacae14,read(0xacae14)^value)
                if mask&4:put(0x8c4714,0)
                if mask&512:put(MOUSE+16,value)
            else:
                if mask&64:put(0x8c4714,NOTIFY_B);put(0x8c45fc,0)
                if mask&256:put(0x8c4714,0)
        elif address==CONVERT:
            window,point=struct.unpack('<2I',cpu.mem_read(stack,8))
            x,y=struct.unpack('<2I',cpu.mem_read(point,8));log(3,window,x,y)
            put(point,script['cx']);put(point+4,script['cy'])
            if mask&8:
                put(0xacadb0,read(0xacadb0)^value);put(MOUSE+24,value^0x1100);put(MOUSE+20,value^0x2200)
            cpu.reg_write(oracle.reg.UC_X86_REG_EAX,script['success'])
        elif address==POSITION:
            x,y=struct.unpack('<2I',cpu.mem_read(stack,8));log(4,x,y)
            if mask&16:put(MOUSE+16,value)
            cpu.reg_write(oracle.reg.UC_X86_REG_EAX,0)
        elif address==CURSOR:
            log(5,read(stack))
            if mask&32:put(MOUSE+24,value^0x3300);put(MOUSE+20,value^0x4400)
            cpu.reg_write(oracle.reg.UC_X86_REG_EAX,0xdeadbeef)
        else:
            log(6,address,read(stack))
            if mask&128:
                put(0x8c4714,0);put(0xacae14,read(0xacae14)^value);put(MOUSE+16,read(MOUSE+16)^1)
    bindings=((0x83b270,ENTER,4),(0x83b274,LEAVE,4),(0x83b45c,CONVERT,8),
              (0x83b384,POSITION,8),(0x83b434,CURSOR,4))
    saved={iat:bytes(cpu.mem_read(iat,4)) for iat,_,_ in bindings}
    saved[0x8c4938]=bytes(cpu.mem_read(0x8c4938,4))
    for address in (QUERY,CTOR,CONTEXT,DTOR):saved[address]=bytes(cpu.mem_read(address,3))
    for iat,stub,cleanup in bindings:
        put(iat,stub);cpu.mem_write(stub,b'\xc2'+struct.pack('<H',cleanup))
    put(0x8c4938,GATE)
    for address in (QUERY,CTOR,CONTEXT,DTOR,GATE,NOTIFY_A,NOTIFY_B):cpu.mem_write(address,b'\xc3')
    if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
    addresses=(ENTER,LEAVE,CONVERT,POSITION,CURSOR,NOTIFY_A,NOTIFY_B,QUERY,CTOR,CONTEXT,DTOR,GATE)
    hooks=[cpu.hook_add(UC_HOOK_CODE,observe,begin=a,end=a) for a in addresses]
    cases=[]
    try:
        for inputs in rows():
            operation,first,second,mask,value,success,cx,cy,enabled,callback,px,py,*rest=inputs
            args=rest[:4];globals=rest[4:4+SIZE];image=rest[4+SIZE:]
            script.update(mask=mask,value=value,success=success,cx=cx,cy=cy,queries=(first,second),query_count=0)
            cpu.mem_write(GLOBALS,bytes(globals));cpu.mem_write(MOUSE,bytes(image))
            put(0x8c45fc,enabled);put(0x8c4714,callback);put(0x8c4600,px);put(0x8c4604,py);logs.clear()
            oracle.call(0x6f0720 if operation==0 else 0x6f07f0,args if operation==0 else args[:2],instruction_limit=100000)
            cases.append(dict(input=inputs,output=[read(0x8c4600),read(0x8c4604),read(0x8c45fc),read(0x8c4714),
                *cpu.mem_read(GLOBALS,SIZE),*cpu.mem_read(MOUSE,28),len(logs),*(v for row in logs for v in row)]))
    finally:
        for hook in hooks:cpu.hook_del(hook)
        for address,data in saved.items():cpu.mem_write(address,data)
        if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
    return cases
