"""Reusable thread resource adapter; never runs Windows imports or thread cleanup."""
import struct
from contextlib import contextmanager
from tools.startup_thread_runtime_cases import GLOBALS,IAT
class ThreadOracle:
 def __init__(self,oracle):self.oracle=oracle
 def word(self,a):return struct.unpack('<I',self.oracle.cpu.mem_read(a,4))[0]
 def put(self,a,v):self.oracle.cpu.mem_write(a,struct.pack('<I',v&0xffffffff))
 def values(self):return [self.word(a) for a in GLOBALS]
 def reset(self,profile):
  self.profile=profile;self.logs=[];self.process_calls=0
  for a in GLOBALS:self.put(a,0)
 def output(self):return [*self.values(),len(self.logs),*self.logs]
 def observe(self,cpu,a,size,user):
  stack=cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP);arg=lambda i:self.word(stack+4+i*4)
  if a in (0x6bd640,0x6ee770):
   if not 0x6be570<=self.word(stack)<0x6be5e0:return
   id=1 if a==0x6bd640 else 4
  elif a==0x6be3b0:id=9
  else:id=(a-0x7000a000)//16
  n={1:0,2:0,3:4,4:3,5:0,6:0,7:0,8:7,9:0}[id];args=[arg(i) for i in range(n)]
  self.logs.extend((id,n,*args,*self.values()));result=0
  if id==1:result=0x12345678
  elif id==2:self.put(arg(0)+4,4096)
  elif id==3:result=0 if self.profile&4 else 0x71003000
  elif id==4:
   if self.profile&8:self.put(GLOBALS[4],0x71004000);self.put(GLOBALS[5],0xcafe)
  elif id==5:result=0x1234
  elif id==6:self.process_calls+=1;result=0xa000+self.process_calls
  elif id==7:result=0xb000
  elif id==8:
   result=0 if self.profile&16 else 1
   if not self.profile&16:self.put(args[3],0xc000)
  cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX,result)
  if a==0x6ee770:cpu.reg_write(self.oracle.reg.UC_X86_REG_EIP,0x7000a100)
 @contextmanager
 def substituted(self):
  from unicorn import UC_HOOK_CODE
  cpu=self.oracle.cpu;saved={a:bytes(cpu.mem_read(a,4)) for a in (*IAT,0x6bd640,0x6be3b0)};hooks=[]
  try:
   for a in (0x6bd640,0x6be3b0):cpu.mem_write(a,b'\xc3')
   cpu.mem_write(0x7000a100,b'\xc3')
   for a,(id,cleanup) in IAT.items():
    stub=0x7000a000+id*16;self.put(a,stub);cpu.mem_write(stub,b'\xc2'+struct.pack('<H',cleanup));hooks.append(cpu.hook_add(UC_HOOK_CODE,self.observe,begin=stub,end=stub))
   for a in (0x6bd640,0x6ee770,0x6be3b0):hooks.append(cpu.hook_add(UC_HOOK_CODE,self.observe,begin=a,end=a))
   if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
   yield
  finally:
   for h in hooks:cpu.hook_del(h)
   for a,data in saved.items():cpu.mem_write(a,data)
   if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
