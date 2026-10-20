"""Original string query and actual strncpy; profile/registry are explicit boundaries."""
import struct
from contextlib import contextmanager
OWNER,NAME,OUTPUT=0x71002000,0x71001000,0x71003000
COUNTS=(0,1,2,4,16,254,255,256)
def payload(seed):return (b'',b'A',b'Hello',b'\x80Z',b'X'*255,b'Y'*254,b'A\0TAIL',b'Q'*16)[(seed%64+(seed//64)%8+seed//512)%8]
class StringOracle:
 def __init__(self,oracle):self.oracle=oracle
 def word(self,a):return struct.unpack('<I',self.oracle.cpu.mem_read(a,4))[0]
 def put(self,a,v):self.oracle.cpu.mem_write(a,struct.pack('<I',v&0xffffffff))
 def observe(self,cpu,a,size,user):
  stack=cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP);arg=lambda i:self.word(stack+4+i*4)
  if a==0x7000d300:id=1;args=[arg(0)-OWNER,arg(1),arg(2),arg(4),arg(5)-OWNER];buffer=arg(3);metadata=[]
  elif a==0x7000d400:id=2;args=[arg(i) for i in range(3)];buffer=arg(4);metadata=[self.word(arg(5))] # Original type is uninitialized; never observe it.
  else:raise AssertionError(hex(a))
  self.logs.extend((id,len(args),*args,*cpu.mem_read(buffer,256),len(metadata),*metadata,*cpu.mem_read(OWNER,0x210),*cpu.mem_read(OUTPUT,320)))
  text=payload(self.seed);cpu.mem_write(buffer,text)
  if id==1:
   if self.profile&32:self.put(OWNER+4,0x10203040)
   result=1 if self.profile&16 else 0
  else:
   self.put(arg(3),2 if self.profile&2 else 1);self.put(arg(5),0 if self.profile&4 else (1 if self.profile&8 else 255))
   if self.profile&32:self.put(OWNER+4,0x20304050)
   result=5 if self.profile&1 else 0
  cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX,result)
 @contextmanager
 def substituted(self):
  from unicorn import UC_HOOK_CODE
  cpu=self.oracle.cpu;iats={0x83b300:(0x7000d300,24),0x83b028:(0x7000d400,24)};saved={a:bytes(cpu.mem_read(a,4)) for a in iats};hooks=[]
  try:
   for a,(stub,n) in iats.items():self.put(a,stub);cpu.mem_write(stub,b'\xc2'+struct.pack('<H',n))
   for a,n in iats.values():hooks.append(cpu.hook_add(UC_HOOK_CODE,self.observe,begin=a,end=a))
   if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
   yield
  finally:
   for h in hooks:cpu.hook_del(h)
   for a,v in saved.items():cpu.mem_write(a,v)
   if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
def capture(oracle):
 b=StringOracle(oracle);cpu=oracle.cpu;cases=[]
 with b.substituted():
  for seed in range(2048):
   b.seed=seed;b.profile=seed%64;b.logs=[];variant=seed//512;name=NAME;present=1;count=COUNTS[(seed//64)%8]
   image=bytearray((seed+i*37)&255 for i in range(0x210));struct.pack_into('<I',image,4,0xfedcba98);image[8]=0 if variant==1 else 75;image[0x10c]=0 if variant==2 else 80
   if variant==3:
    if seed%3==0:struct.pack_into('<I',image,4,0)
    elif seed%3==1:name=0
    else:present=0
   output=bytes((seed+i*13)&255 for i in range(320));cpu.mem_write(OWNER,bytes(image));cpu.mem_write(OUTPUT,output)
   oracle.call(0x51d7c0,(name,OUTPUT if present else 0,count),this_pointer=OWNER,cleanup=b'',instruction_limit=30000)
   result=cpu.reg_read(oracle.reg.UC_X86_REG_EAX)&255
   cases.append(dict(input=[seed,b.profile,name,present,count,*image,*output],output=[result,*cpu.mem_read(OWNER,0x210),*cpu.mem_read(OUTPUT,320),len(b.logs),*b.logs]))
 return cases
