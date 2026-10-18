"""Original message dispatcher/procedure with declared platform/handler scripts."""
import struct
BASE,SIZE,TABLE,COUNT,SYNC=0xaca8f0,0x530,0x28,0x4f4,0x524
ENTER,LEAVE,A,B=0x70008000,0x70008100,0x70009000,0x70009100
DEFAULT=0x70009200
RESULT=0x71003000


def fixture_rows(window_procedure=False):
    for n in (0,1,2,3,4,7,8,127,128):
        keys=[0x100+i*3 for i in range(n)]
        queries=[0xff,0x100,0x103,0x100+(n//2)*3,0x100+n*3,0xffffffff]
        if n==128:queries+=keys
        for query in queries:
            masks=(0,1,2,4,8,16,32,64,127)+(128,192,256,320) if window_procedure else (0,1,2,4,8,16,32,64,127)
            for mask in masks:yield keys,query,mask
    for query in (0,1,0x7fffffff,0x80000000,0xffffffff):
        for keys in ((0,0x7fffffff,0x80000000,0xffffffff),(0x100,)*4,(7,3,0x100,1)):
            yield keys,query,0


def capture(oracle,window_procedure=False):
    from unicorn import UC_HOOK_CODE
    cpu=oracle.cpu;result=[]
    def word(offset):return struct.unpack('<I',cpu.mem_read(BASE+offset,4))[0]
    def put(offset,value):cpu.mem_write(BASE+offset,struct.pack('<I',value&0xffffffff))
    def enabled():return struct.unpack('<I',cpu.mem_read(0x89bdd4,4))[0]
    def set_enabled(value):cpu.mem_write(0x89bdd4,struct.pack('<I',value&0xffffffff))
    logs=[];script={}
    def observe(cpu,address,size,user):
        if address in (ENTER,LEAVE):
            identity=struct.unpack('<I',cpu.mem_read(cpu.reg_read(oracle.reg.UC_X86_REG_ESP)+4,4))[0]
            logs.append([1 if address==ENTER else 2,identity,enabled(),word(COUNT),word(SYNC),word(TABLE),word(TABLE+4),0])
            mask,value=script['mask'],script['value']
            if address==ENTER:
                if mask&1:set_enabled(0)
                if mask&2:put(COUNT,1);put(TABLE,script['message']);put(TABLE+4,B)
                if mask&4:put(SYNC,word(SYNC)^value)
                if mask&8:put(COUNT,0)
            else:
                if mask&32:set_enabled(enabled()^1)
                if window_procedure and mask&128 and script.get('slot'):
                    cpu.mem_write(script['slot'],struct.pack('<I',value^0x55aa55aa))
        elif address in (A,B):
            args=struct.unpack('<6I',cpu.mem_read(cpu.reg_read(oracle.reg.UC_X86_REG_ESP)+4,24))
            if window_procedure:
                script['slot']=args[5]
                initial=struct.unpack('<I',cpu.mem_read(args[5],4))[0]
                logs.append([3,address,*args[:5],initial])
            else:logs.append([3,address,*args])
            if script['mask']&16:put(SYNC,word(SYNC)^script['value']^0x11223344)
            if script['mask']&64 and args[5]:cpu.mem_write(args[5],struct.pack('<I',script['value']))
            cpu.reg_write(oracle.reg.UC_X86_REG_EAX,(script['retval']+int(address==B))&0xffffffff)
        elif address==DEFAULT:
            args=struct.unpack('<4I',cpu.mem_read(cpu.reg_read(oracle.reg.UC_X86_REG_ESP)+4,16))
            logs.append([4,*args,enabled(),word(COUNT),word(SYNC)])
            if script['mask']&256:set_enabled(0)
            cpu.reg_write(oracle.reg.UC_X86_REG_EAX,script['value']^0x87654321)
    saved={a:bytes(cpu.mem_read(a,4)) for a in (0x83b270,0x83b274,0x83b380)}
    for iat,stub in ((0x83b270,ENTER),(0x83b274,LEAVE)):
        cpu.mem_write(iat,struct.pack('<I',stub));cpu.mem_write(stub,b'\xc2\x04\x00')
    for stub in (A,B):cpu.mem_write(stub,b'\xc2\x18\x00')
    cpu.mem_write(DEFAULT,b'\xc2\x10\x00');cpu.mem_write(0x83b380,struct.pack('<I',DEFAULT))
    hook=cpu.hook_add(UC_HOOK_CODE,observe,begin=ENTER,end=DEFAULT)
    try:
        for i,(keys,message,mask) in enumerate(fixture_rows(window_procedure)):
            image=bytearray((i+j*37)&255 for j in range(SIZE))
            struct.pack_into('<I',image,COUNT,len(keys));struct.pack_into('<I',image,SYNC,0x12345678)
            for j,key in enumerate(keys):struct.pack_into('<2I',image,TABLE+j*8,key,A if j%2==0 else B)
            active=0 if i%17==0 else 0x80000000 if i%7==0 else 1
            value=(0xaabbccdd^i)&0xffffffff;retval=(0,1,0xffffffff)[i%3]
            target=RESULT if i%2 else 0
            script.update(mask=mask,value=value,retval=retval,message=message,slot=0)
            cpu.mem_write(BASE,bytes(image));set_enabled(active);cpu.mem_write(RESULT,b'\x11\x22\x33\x44');logs.clear()
            if window_procedure:
                oracle.call(0x583290,(7,message,0x76543210,0x81000001),cleanup=b'')
            else:oracle.call(0x583210,(7,message,0x76543210,0x81000001,target))
            result.append(dict(input=[active,mask,value,retval,7,message,0x76543210,0x81000001,target,*image,17,34,51,68],
                output=[cpu.reg_read(oracle.reg.UC_X86_REG_EAX),enabled(),*cpu.mem_read(BASE,SIZE),
                        *cpu.mem_read(RESULT,4),len(logs),*(v for log in logs for v in log)]))
    finally:
        cpu.hook_del(hook)
        for address,data in saved.items():cpu.mem_write(address,data)
        if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
    return result
