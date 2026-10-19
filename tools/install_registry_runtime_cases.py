"""Whole original registry-owner image, with explicit synthetic platform boundaries."""
import struct
from contextlib import contextmanager
OWNER,SOURCE=0x71002000,0x71001000
ENTRIES=(0x51d330,0x51d580,0x51d490,0x530ab0,0x51d3c0)
def module_path(seed):return (b"C:\\Games\\mcity.exe",b"C:\\Games\\Nps\\mcity.exe",b"mcity.exe",b"C:\\NpsElse\\game\\mcity.exe",b"\\nPs\\game.exe",b"C:\\single.exe",b"C:\\"+b"a"*230+b"\\m.exe",b"FAILURE-WRITE")[seed%8]
def source(seed):return bytes(65+(seed+i)%26 for i in range((0,3,258,300)[seed%4]))
class RegistryOracle:
 def __init__(self,oracle):self.oracle=oracle
 def word(self,a):return struct.unpack('<I',self.oracle.cpu.mem_read(a,4))[0]
 def put(self,a,v):self.oracle.cpu.mem_write(a,struct.pack('<I',v&0xffffffff))
 def observe(self,cpu,a,size,user):
  stack=cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP);arg=lambda i:self.word(stack+4+i*4);result=0
  if a==0x699390:id=4;args=[arg(0)-OWNER,arg(1),arg(2)]
  elif a==0x7000d100:id=2;args=[arg(0)]
  elif a==0x7000d200:id=5 if self.mode==3 else 3;args=[arg(i) for i in range(4)]
  elif a==0x7000d400:id=7;args=[arg(0),arg(1)-OWNER,arg(2)]
  elif a==0x7000d300:id=6;args=[arg(0),arg(1),arg(2),self.word(arg(3)),self.word(arg(5)),self.word(arg(4))]
  else:raise AssertionError(hex(a))
  self.logs.extend((id,len(args),*args,*cpu.mem_read(OWNER,0x210),self.word(0xa55468)))
  if id==7:
   text=module_path(self.seed);cpu.mem_write(arg(1),text+b'\0');result=0 if self.seed%8==7 else len(text)
   if self.profile&4:self.put(OWNER+4,0xdead1234)
  elif id==2:
   if self.profile&8:self.put(OWNER+4,0xcafef00d);cpu.mem_write(OWNER+8,b'Z');cpu.mem_write(OWNER+0x10c,b'Q')
   result=123
  elif id in (3,5):
   self.put(arg(4),0 if id==3 and self.profile&2 else 0x12345678)
   if self.profile&16:cpu.mem_write(OWNER+8,b'R');cpu.mem_write(OWNER+0x10c,b'S')
   result=5 if id==3 and self.profile&1 else 0
  elif id==4:
   text=source(self.seed);cpu.mem_write(arg(0),text[:arg(2)]+bytes(max(0,arg(2)-len(text))))
   if self.profile&32:self.put(OWNER+4,0x87654321)
   result=arg(0)
  elif id==6:
   if not self.profile&1:
    value=0x12340000+self.seed
    cpu.mem_write(arg(4),struct.pack('<I',value)[:2 if self.profile&2 else 4])
   if self.profile&16:self.put(arg(3),7);self.put(arg(5),2)
   result=234 if self.profile&1 else 0
  cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX,result)
 @contextmanager
 def substituted(self):
  from unicorn import UC_HOOK_CODE
  cpu=self.oracle.cpu;addresses=(0x699390,);iats={0x83b010:0x7000d100,0x83b018:0x7000d200,0x83b028:0x7000d300,0x83b288:0x7000d400};saved={a:bytes(cpu.mem_read(a,4)) for a in (*addresses,*iats)};hooks=[];old_locale=self.word(0xb2b5b4)
  try:
   for a in addresses:cpu.mem_write(a,b'\xc3')
   for a,stub in iats.items():self.put(a,stub);cpu.mem_write(stub,b'\xc2'+struct.pack('<H',{0x83b010:4,0x83b018:20,0x83b028:24,0x83b288:12}[a]))
   for a in (*addresses,*iats.values()):hooks.append(cpu.hook_add(UC_HOOK_CODE,self.observe,begin=a,end=a))
   if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
   self.put(0xb2b5b4,0)
   yield
  finally:
   self.put(0xb2b5b4,old_locale)
   for h in hooks:cpu.hook_del(h)
   for a,b in saved.items():cpu.mem_write(a,b)
   if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
def capture(oracle):
 b=RegistryOracle(oracle);cpu=oracle.cpu;cases=[]
 with b.substituted():
  for mode in range(5):
   for seed in range(256):
    b.mode=mode;b.seed=seed;b.profile=(seed//4)%64;b.logs=[]
    image=bytearray((seed+i*37)&255 for i in range(0x210));struct.pack_into('<I',image,4,0 if seed&64 else 0xfedcba98);cpu.mem_write(OWNER,bytes(image));cpu.mem_write(SOURCE,source(seed)+b'\0');b.put(0xa55468,0xa5000000+seed)
    args=(0x80000002,SOURCE,0xf003f) if mode in (0,1) else ()
    oracle.call(ENTRIES[mode],args,this_pointer=OWNER,cleanup=b'',instruction_limit=10000)
    result=cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
    if mode in (1,2):result&=255
    if mode in (3,4):result=0
    cases.append(dict(input=[mode,seed,b.profile,*image,0xa5000000+seed],output=[result,*cpu.mem_read(OWNER,0x210),b.word(0xa55468),len(b.logs),*b.logs]))
 return cases
