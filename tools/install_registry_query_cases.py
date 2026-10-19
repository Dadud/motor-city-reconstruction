"""Synthetic registry reads/creation/close; no host registry or account values."""
import struct
from contextlib import contextmanager
OWNER,NAME,OUTPUT=0x71002000,0x71001000,0x71003000
ENTRIES=(0x51d1d0,0x51d520,0x51d6c0,0x51d690)
class QueryOracle:
 def __init__(self,oracle):self.oracle=oracle
 def word(self,a):return struct.unpack('<I',self.oracle.cpu.mem_read(a,4))[0]
 def put(self,a,v):self.oracle.cpu.mem_write(a,struct.pack('<I',v&0xffffffff))
 def observe(self,cpu,a,size,user):
  stack=cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP);arg=lambda i:self.word(stack+4+i*4)
  metadata=[];text=[];buffer=b''
  if a==0x7000d100:id=1;args=[arg(0)]
  elif a==0x7000d200:id=2;args=[arg(i) for i in range(7)];metadata=[self.word(arg(8))];buffer=cpu.mem_read(arg(7),4)
  elif a==0x7000d300:id=3;args=[arg(0)-OWNER,arg(1),arg(2),arg(4),arg(5)-OWNER];buffer=cpu.mem_read(arg(3),256)
  elif a==0x7000d400:id=4;args=[arg(i) for i in range(3)];metadata=[self.word(arg(3)),self.word(arg(5))];buffer=cpu.mem_read(arg(4),4)
  elif a==0x6995db:id=5;args=[arg(1)];buffer=cpu.mem_read(arg(2),4);text=cpu.mem_read(arg(0),256)
  else:raise AssertionError(hex(a))
  self.logs.extend([id,len(args),*args,len(buffer),*buffer,len(metadata),*metadata,len(text),*text,*cpu.mem_read(OWNER,0x210),*cpu.mem_read(OUTPUT,4)])
  result=0
  if id==1:
   if self.profile&32:self.put(OWNER+4,0xdeadbeef);cpu.mem_write(OWNER+8,b'Z');cpu.mem_write(OWNER+0x10c,b'Q')
   result=17
  elif id==2:
   self.put(arg(7),0x12345678);self.put(arg(8),2)
   if self.profile&32:cpu.mem_write(OWNER+8,b'R');cpu.mem_write(OWNER+0x10c,b'S')
   result=5 if self.profile&1 else 0
  elif id==3:
   if self.profile&16:
    if self.seed%7:cpu.mem_write(arg(3),b'37\0')
    result=1
   if self.profile&32:self.put(OWNER+4,0x10203040)
  elif id==4:
   self.put(arg(3),1 if self.profile&2 else 4);self.put(arg(5),0 if self.profile&4 else (2 if self.profile&8 else 4))
   cpu.mem_write(arg(4),struct.pack('<I',0xa5000000+self.seed)[:2 if self.profile&8 else 4]);result=5 if self.profile&1 else 0
   if self.profile&32:self.put(OWNER+4,0x20304050)
  elif id==5:
   if self.seed%5:self.put(arg(2),0x12340000+self.seed);result=1
  cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX,result)
 @contextmanager
 def substituted(self):
  from unicorn import UC_HOOK_CODE
  cpu=self.oracle.cpu;iats={0x83b010:(0x7000d100,4),0x83b020:(0x7000d200,36),0x83b300:(0x7000d300,24),0x83b028:(0x7000d400,24)}
  saved={a:bytes(cpu.mem_read(a,4)) for a in (*iats,0x6995db)};hooks=[]
  try:
   cpu.mem_write(0x6995db,b'\xc3')
   for a,(stub,n) in iats.items():self.put(a,stub);cpu.mem_write(stub,b'\xc2'+struct.pack('<H',n))
   for a in (0x6995db,*(s for s,n in iats.values())):hooks.append(cpu.hook_add(UC_HOOK_CODE,self.observe,begin=a,end=a))
   if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
   yield
  finally:
   for h in hooks:cpu.hook_del(h)
   for a,v in saved.items():cpu.mem_write(a,v)
   if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
def capture(oracle):
 b=QueryOracle(oracle);cpu=oracle.cpu;cases=[]
 with b.substituted():
  for mode in range(5):
   for seed in range(256):
    b.seed=seed;b.profile=seed%64;b.logs=[]
    image=bytearray((seed+i*37)&255 for i in range(0x210));struct.pack_into('<I',image,4,0 if seed//64==1 else 0xfedcba98);image[8]=0 if seed//64==2 else 75;image[0x10c]=0 if seed//64==3 else 80
    cpu.mem_write(OWNER,bytes(image));cpu.mem_write(OUTPUT,bytes.fromhex('55667788'));name=0 if seed%17==0 else NAME
    out=[]
    for step in ((2,3,1,2,0,3) if mode==4 else (mode,)):
     args=() if step==0 else (0x80000002,NAME,0xf003f) if step==1 else (name,OUTPUT)
     oracle.call(ENTRIES[step],args,this_pointer=OWNER,cleanup=b'',instruction_limit=10000)
     result=0 if step==0 else cpu.reg_read(oracle.reg.UC_X86_REG_EAX)&255
     out.extend([result,*cpu.mem_read(OWNER,0x210),*cpu.mem_read(OUTPUT,4),len(b.logs),*b.logs])
    cases.append(dict(input=[mode,seed,b.profile,name,*image],output=out))
 return cases
