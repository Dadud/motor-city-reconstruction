"""Complete registration with actual original CRT search/sort/comparator bodies."""
import random
import struct
from tools.window_dispatch_cases import BASE,SIZE,TABLE,COUNT,SYNC,ENTER,LEAVE,A,B
CREATE=0x6bd640


def fixtures():
    rng=random.Random(0x582e40)
    for count in (0,1,2,3,7,8,9,16,31,127,128):
        keys=[0x100+i*3 for i in range(count)]
        tables=[keys]
        if count:tables += [list(reversed(keys)),[0x100]*count,[rng.getrandbits(32) for _ in range(count)]]
        for table in tables:
            for message in (0xff,0x100,table[count//2] if count else 0x103,0x7fffffff,0xffffffff):
                for handler in (0,A,B):yield table,message,handler,0
        for mask in (1,2,4,8,32,256):
            for handler in (0,A,B):yield keys,0x100,handler,mask


def capture(oracle,initialize=False):
    from unicorn import UC_HOOK_CODE
    cpu=oracle.cpu;logs=[];script={};result=[]
    def word(offset):return struct.unpack('<I',cpu.mem_read(BASE+offset,4))[0]
    def put(offset,value):cpu.mem_write(BASE+offset,struct.pack('<I',value&0xffffffff))
    def enabled():return struct.unpack('<I',cpu.mem_read(0x89bdd4,4))[0]
    def set_enabled(value):cpu.mem_write(0x89bdd4,struct.pack('<I',value&0xffffffff))
    def observe(cpu,address,size,user):
        identity=0 if address==CREATE else struct.unpack('<I',cpu.mem_read(cpu.reg_read(oracle.reg.UC_X86_REG_ESP)+4,4))[0]
        logs.append([0 if address==CREATE else 1 if address==ENTER else 2,identity,
                     enabled(),word(COUNT),word(SYNC),word(TABLE),word(TABLE+4),0])
        mask,value=script['mask'],script['value']
        if address==CREATE:
            if mask&256:put(COUNT,0)
            cpu.reg_write(oracle.reg.UC_X86_REG_EAX,(script['created']+script['creation_calls']*script['stride'])&0xffffffff)
            script['creation_calls']+=1
        elif address==ENTER:
            if mask&1:set_enabled(0)
            if mask&2:put(COUNT,1);put(TABLE,script['message']);put(TABLE+4,B)
            if mask&4:put(SYNC,word(SYNC)^value)
            if mask&8:put(COUNT,0)
        elif mask&32:set_enabled(enabled()^1)
    saved={a:bytes(cpu.mem_read(a,4)) for a in (0x83b270,0x83b274)}
    create_bytes=bytes(cpu.mem_read(CREATE,1));cpu.mem_write(CREATE,b'\xc3')
    for iat,stub in ((0x83b270,ENTER),(0x83b274,LEAVE)):
        cpu.mem_write(iat,struct.pack('<I',stub));cpu.mem_write(stub,b'\xc2\x04\x00')
    if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
    hooks=[cpu.hook_add(UC_HOOK_CODE,observe,begin=a,end=a) for a in (CREATE,ENTER,LEAVE)]
    try:
        if initialize:
            from tools.window_initialization_cases import fixtures as initialization_fixtures
            rows=initialization_fixtures()
        else:
            rows=((keys,message,handler,mask,None,None,None,0) for keys,message,handler,mask in fixtures())
        for i,(keys,message,handler,mask,flag,synchronizer,created_override,stride) in enumerate(rows):
            image=bytearray((i+j*37)&255 for j in range(SIZE))
            struct.pack_into('<I',image,COUNT,len(keys));struct.pack_into('<I',image,SYNC,0 if i%2 else 0x12345678)
            if flag is not None:struct.pack_into('<I',image,0x51c,flag)
            if synchronizer is not None:struct.pack_into('<I',image,SYNC,synchronizer)
            for j,key in enumerate(keys):struct.pack_into('<2I',image,TABLE+j*8,key,A+j*16)
            active=0 if i%3==0 else 1;value=0xaabbccdd^i;created=0 if i%9==0 else 0x87654321
            if created_override is not None:created=created_override
            script.update(mask=mask,value=value,created=created,message=message,stride=stride,creation_calls=0)
            cpu.mem_write(BASE,bytes(image));set_enabled(active);logs.clear()
            if initialize:oracle.call(0x583c30,instruction_limit=1_000_000)
            else:oracle.call(0x582e40,(message,handler),cleanup=b'',instruction_limit=1_000_000)
            inputs=[active,mask,value,created,stride,*image] if initialize else [active,mask,value,created,message,handler,*image]
            result.append(dict(input=inputs,
                output=[cpu.reg_read(oracle.reg.UC_X86_REG_EAX),enabled(),*cpu.mem_read(BASE,SIZE),
                        len(logs),*(v for row in logs for v in row)]))
    finally:
        for hook in hooks:cpu.hook_del(hook)
        for address,data in saved.items():cpu.mem_write(address,data)
        cpu.mem_write(CREATE,create_bytes)
        if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
    return result
