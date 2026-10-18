"""Complete original mouse/cursor bodies with declared platform callback scripts."""
import struct
GLOBALS,SIZE,MOUSE=0xaca8f0,0x530,0xb36574
ENTER,LEAVE=0x70008000,0x70008100
NOTIFY_A,NOTIFY_B,CONVERT,POSITION,CURSOR=0x7000a000,0x7000a100,0x7000a200,0x7000a300,0x7000a400
CREATE,DEFAULT=0x6bd640,0x7000a500
NAMES=('input_cursor_warp','input_mouse_update','input_mouse_press','input_mouse_motion')
ENTRIES=(0x582fe0,0x6f08d0,0x584670,0x5846d0)


def fixtures(operation):
    bounds=((-10,100,-20,80),(10,-10,20,-20),(-2147483648,2147483647,-2147483648,2147483647),(0,0,0,0))
    positions=((-11,-21),(-10,-20),(0,0),(100,80),(101,81),(-2147483648,2147483647),(65535,32768))
    rows=[]
    for box in bounds:
        for x,y in positions:
            for mask in (0,1,2,4,8,16,32,64,128,256,512,1023):rows.append((box,x,y,mask,None))
    if operation>=2:
        for flags in (*range(256),0x80000000,0xffffffff):rows.append((bounds[0],65535,32768,0,flags))
    for i,(box,x,y,mask,flags) in enumerate(rows):
        lo_x,hi_x,lo_y,hi_y=box
        globals=bytearray((i+j*37)&255 for j in range(SIZE))
        struct.pack_into('<I',globals,0x4c0,7)
        struct.pack_into('<I',globals,0x524,0 if i%13==0 else 0x12345678)
        image=struct.pack('<7I',hi_x&0xffffffff,hi_y&0xffffffff,lo_y&0xffffffff,lo_x&0xffffffff,
                          0x87654321,0x10203040,0x50607080)
        active=0 if i%17==0 else 0x80000000 if i%7==0 else 1
        callback=0 if i%11==0 else NOTIFY_A
        value=0x11223344^i
        converted=(0x76543210^i,0x89abcdef^i)
        success=(0,1,0x80000000)[i%3]
        if operation==0:args=[x&0xffffffff,y&0xffffffff,0,0,0,0]
        elif operation==1:args=[x&0xffffffff,y&0xffffffff,0xabcd0000|i,0 if i%3==0 else 1,0,0]
        else:args=[0 if i%19==0 else 1,8 if i%23==0 else 7,0x201 if operation==2 else 0x200,
                   flags if flags is not None else (i*37)&0xffffffff,((y&65535)<<16)|(x&65535),0]
        yield [mask,value,success,*converted,active,callback,*args,*globals,*image]


def lifecycle_rows():
    base=next(fixtures(2))
    for variant,mask in enumerate((0,0,64,130)):
        inputs=list(base);inputs[0]=mask;inputs[1]^=variant;inputs[2]=variant&1;inputs[5]=1
        inputs[6]=0 if variant==1 else NOTIFY_A
        globals=bytearray(inputs[13:13+SIZE])
        for offset in (0x4f4,0x51c,0x524):struct.pack_into('<I',globals,offset,0)
        inputs[13:13+SIZE]=globals
        inputs[13+SIZE:]=struct.pack('<7I',100,80,0,0,0,0,0)
        def point(x,y):return ((y&65535)<<16)|(x&65535)
        steps=[(0,0,0,0),(0,0,0,0),(2,1,0,0),(1,0x201,1,point(-1,10)),
               (2,1,0,0),(1,0x200,0x13,point(10,20)),(2,1,0,0),(1,0x202,0,point(15,25)),
               (2,1,0,0),(1,0x203,2,point(30,40)),(2,1,0,0),(1,0x207,16,point(200,90)),
               (3,0,0,0),(1,0x201,1,point(5,6)),(3,1,0,0),(2,1,0,0),
               (1,0x205,0,point(65535,32768)),(1,0x777,0x1234,0x5678),(0,0,0,0)]
        yield variant&1,inputs,steps


def capture(oracle,name,lifecycle=False):
    from unicorn import UC_HOOK_CODE
    operation=NAMES.index(name);cpu=oracle.cpu;result=[];logs=[];script={}
    def read(a):return struct.unpack('<I',cpu.mem_read(a,4))[0]
    def put(a,v):cpu.mem_write(a,struct.pack('<I',v&0xffffffff))
    def log(kind,a=0,b=0,c=0,d=0):
        logs.append([kind,a,b,c,d,read(0x8c45fc),read(0x8c4714),read(0xacae14),read(0xacadb0),
                     *struct.unpack('<7I',cpu.mem_read(MOUSE,28))])
    def observe(cpu,address,size,user):
        stack=cpu.reg_read(oracle.reg.UC_X86_REG_ESP)+4
        mask,value=script['mask'],script['value']
        if address==CREATE:
            log(7)
            cpu.reg_write(oracle.reg.UC_X86_REG_EAX,0x12340000+script['creations']*0x100)
            script['creations']+=1
        elif address==DEFAULT:
            window,message,wparam,lparam=struct.unpack('<4I',cpu.mem_read(stack,16))
            log(8,window,message,wparam,lparam)
            cpu.reg_write(oracle.reg.UC_X86_REG_EAX,0xd3f00000^message)
        elif address in (ENTER,LEAVE):
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
    if lifecycle:bindings+=((0x83b380,DEFAULT,16),)
    saved={iat:bytes(cpu.mem_read(iat,4)) for iat,_,_ in bindings}
    for iat,stub,cleanup in bindings:
        put(iat,stub);cpu.mem_write(stub,b'\xc2'+struct.pack('<H',cleanup))
    for stub in (NOTIFY_A,NOTIFY_B):cpu.mem_write(stub,b'\xc3')
    saved_create=bytes(cpu.mem_read(CREATE,1))
    if lifecycle:cpu.mem_write(CREATE,b'\xc3')
    if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
    addresses=(ENTER,LEAVE,CONVERT,POSITION,CURSOR,NOTIFY_A,NOTIFY_B)+((CREATE,DEFAULT) if lifecycle else ())
    hooks=[cpu.hook_add(UC_HOOK_CODE,observe,begin=a,end=a) for a in addresses]
    try:
        rows=lifecycle_rows() if lifecycle else ((0,inputs,None) for inputs in fixtures(operation))
        for procedure,inputs,steps in rows:
            mask,value,success,cx,cy,active,callback,*rest=inputs
            args=rest[:6];globals=rest[6:6+SIZE];image=rest[6+SIZE:]
            script.update(mask=mask,value=value,success=success,cx=cx,cy=cy,creations=0)
            cpu.mem_write(GLOBALS,bytes(globals));cpu.mem_write(MOUSE,bytes(image))
            put(0x8c45fc,active);put(0x8c4714,callback);logs.clear()
            if lifecycle:
                put(0x89bdd4,1);output=[]
                for op,a,b,c in steps:
                    if op==0:oracle.call(0x583c30,instruction_limit=1_000_000)
                    elif op==1:
                        if procedure:oracle.call(0x583290,(7,a,b,c),cleanup=b'')
                        else:oracle.call(0x583210,(7,a,b,c,0))
                    elif op==2:put(0x8c45fc,a)
                    elif op==3:put(0x89bdd4,a)
                    else:raise ValueError(op)
                    output.extend([cpu.reg_read(oracle.reg.UC_X86_REG_EAX) if op in (0,1) else 0,
                        read(0x89bdd4),read(0x8c45fc),read(0x8c4714),script['creations'],
                        *cpu.mem_read(GLOBALS,SIZE),*cpu.mem_read(MOUSE,28),len(logs),
                        *(v for row in logs for v in row)])
                    logs.clear()
                result.append(dict(input=[procedure,*inputs,len(steps),*(v for row in steps for v in row)],output=output))
                continue
            if operation==0:oracle.call(ENTRIES[operation],(0xacada0,*args[:2]))
            elif operation==1:oracle.call(ENTRIES[operation],args[:4])
            else:oracle.call(ENTRIES[operation],(*args[:5],0xdeadbeef),cleanup=b'')
            result.append(dict(input=inputs,output=[0 if operation<2 else cpu.reg_read(oracle.reg.UC_X86_REG_EAX),
                read(0x8c45fc),read(0x8c4714),*cpu.mem_read(GLOBALS,SIZE),*cpu.mem_read(MOUSE,28),
                len(logs),*(v for row in logs for v in row)]))
    finally:
        for hook in hooks:cpu.hook_del(hook)
        for address,data in saved.items():cpu.mem_write(address,data)
        if lifecycle:cpu.mem_write(CREATE,saved_create)
        if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
    return result


def lifecycle_cases(oracle):
    return dict(cases=capture(oracle,'input_mouse_press',True),
                scope='Initialized general/Windows dispatch through actual mouse update/warp children; only platform/lock/notification bridges substituted.')
