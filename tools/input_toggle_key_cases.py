"""Complete toggle-key bodies with synthetic returning Windows import bridges."""
import struct
QUERY, EVENT = 0x83b3e4, 0x83b3e8
Q, FIRST, SECOND = 0x7000eb00, 0x7000ec00, 0x7000ed00

def capture(oracle):
    from unicorn import UC_HOOK_CODE
    cpu=oracle.cpu
    def put(a,v):cpu.mem_write(a,struct.pack('<I',v))
    def observe(cpu,address,size,user):
        esp=cpu.reg_read(oracle.reg.UC_X86_REG_ESP)
        if address==Q:
            key=struct.unpack('<I',cpu.mem_read(esp+4,4))[0]
            logs.append([0,0,key,0,0,0])
            if script&1:put(EVENT,SECOND)
            cpu.reg_write(oracle.reg.UC_X86_REG_EAX,state)
        else:
            key,scan,flags,extra=struct.unpack('<4I',cpu.mem_read(esp+4,16))
            # Windows declares both key and scan BYTE; upper argument bits are undefined.
            logs.append([1,int(address==SECOND),key&255,scan&255,flags,extra])
            if script&2:put(EVENT,FIRST if address==SECOND else SECOND)
    saved=[bytes(cpu.mem_read(a,4)) for a in (QUERY,EVENT)]
    cpu.mem_write(Q,b'\xc2\x04\x00')
    for a in (FIRST,SECOND):cpu.mem_write(a,b'\xc2\x10\x00')
    hooks=[cpu.hook_add(UC_HOOK_CODE,observe,begin=a,end=a) for a in (Q,FIRST,SECOND)]
    cases=[]
    try:
        for mode in (0,1):
            for selector in ((0,1,2,3,0xffffffff,0x100,0x101,0x102) if mode==0 else (1,)):
                for desired in ((0,1,2,0x80000000,0xffffffff) if mode==0 else (0,)):
                    for state in (0,1,2,0x8000,0xffff,0xffffffff):
                        for script in range(4):
                            logs=[];put(QUERY,Q);put(EVENT,FIRST)
                            oracle.call(0x6bfc90 if mode==0 else 0x6bfc80,
                                        (selector,desired) if mode==0 else ())
                            cases.append(dict(input=[mode,selector,desired,state,script],
                                              output=[len(logs),*(v for row in logs for v in row)]))
    finally:
        for h in hooks:cpu.hook_del(h)
        for a,data in zip((QUERY,EVENT),saved):cpu.mem_write(a,data)
    return cases
