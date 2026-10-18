"""Original thread startup/allocation bodies with explicit OS/resource bridges."""
import struct
GLOBALS=tuple(range(0xb2bbc4,0xb2bbe0,4))+(0xb35fd0,)
IAT={0x83b20c:(2,4),0x83b26c:(3,16),0x83b0ac:(5,0),0x83b14c:(6,0),0x83b184:(7,0),0x83b210:(8,28)}
DIRECT={0x6bd640:1,0x6ee770:4}
ENTRIES=(0x6be4f0,0x6be570,0x6eedb0)

def capture(oracle):
 from unicorn import UC_HOOK_CODE
 cpu=oracle.cpu;cases=[];logs=[];profile=0;process_calls=0
 def word(a):return struct.unpack('<I',cpu.mem_read(a,4))[0]
 def put(a,v):cpu.mem_write(a,struct.pack('<I',v&0xffffffff))
 def values():return [word(a) for a in GLOBALS]
 def observe(cpu,address,size,user):
  nonlocal process_calls
  id=DIRECT.get(address,(address-0x7000a000)//16)
  stack=cpu.reg_read(oracle.reg.UC_X86_REG_ESP);arg=lambda i:word(stack+4+i*4)
  n={1:0,2:0,3:4,4:3,5:0,6:0,7:0,8:7}[id]
  args=[arg(i) for i in range(n)]
  logs.extend((id,n,*args,*values()));result=0
  if id==1:result=0 if profile&1 else 0x71002000
  elif id==2:put(arg(0)+4,8192 if profile&2 else 4096)
  elif id==3:result=0 if profile&4 else 0x71003000
  elif id==4:
   if profile&8:put(GLOBALS[4],0x71004000);put(GLOBALS[5],0xcafe)
  elif id==5:result=0x1234
  elif id==6:process_calls+=1;result=0xa000+process_calls
  elif id==7:result=0xb000
  elif id==8:
   result=0 if profile&16 else 1
   if not profile&16:put(arg(3),0xc000)
   if profile&32:put(GLOBALS[3],1)
  cpu.reg_write(oracle.reg.UC_X86_REG_EAX,result)
 saved={a:bytes(cpu.mem_read(a,1)) for a in DIRECT};saved_iat={a:word(a) for a in IAT};hooks=[]
 try:
  for a in DIRECT:cpu.mem_write(a,b'\xc3');hooks.append(cpu.hook_add(UC_HOOK_CODE,observe,begin=a,end=a))
  for a,(id,cleanup) in IAT.items():
   stub=0x7000a000+id*16;put(a,stub);cpu.mem_write(stub,b'\xc2'+struct.pack('<H',cleanup));hooks.append(cpu.hook_add(UC_HOOK_CODE,observe,begin=stub,end=stub))
  for mode in range(4):
   for seed in range(256):
    profile=seed%64;count=(0,1,100,341,342,4096,0x7fffffff,0x80000000,0xffffffff,0x15555555)[seed%10]
    initial=[0xd00d,0xeeee,0 if seed&1 else 7,0 if seed&2 else 9,0 if seed&4 else 0x71005000,0x123,0 if seed&8 else 0x71006000,(0,4096,8192)[seed%3]]
    slots=[0 if seed&16 else (0x6be3b0 if i==seed%64 else 0x123000+i) for i in range(64)]
    for a,v in zip(GLOBALS,initial):put(a,v)
    for i,v in enumerate(slots):put(0xb2bbe8+i*4,v)
    logs.clear();process_calls=0;put(0x71001000,count)
    results=[]
    steps=((0,count),(1,count),(0,count+1),(1,count+1)) if mode==3 else ((mode,count),)
    for which,arg in steps:
     oracle.call(ENTRIES[which],(0x71001000 if which==2 else arg,),instruction_limit=10000)
     results.append(cpu.reg_read(oracle.reg.UC_X86_REG_EAX) if which in (1,2) else 0)
    cases.append(dict(input=[mode,count,profile,*initial,*slots],output=[*results,word(0x71001000),*values(),*(word(0xb2bbe8+i*4) for i in range(64)),len(logs),*logs]))
 finally:
  for h in hooks:cpu.hook_del(h)
  for a,b in saved.items():cpu.mem_write(a,b)
  for a,v in saved_iat.items():put(a,v)
  if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
 return cases
