"""Installation helpers; real original sprintf executes, drive API is synthetic."""
import struct

def capture(oracle):
 from unicorn import UC_HOOK_CODE
 cpu=oracle.cpu;cases=[];drive=[];api=0
 def observe(cpu,a,n,u):
  at=cpu.reg_read(oracle.reg.UC_X86_REG_ESP)+4
  p=struct.unpack('<I',cpu.mem_read(at,4))[0]
  drive.extend(cpu.mem_read(p,4));cpu.reg_write(oracle.reg.UC_X86_REG_EAX,api)
 saved=bytes(cpu.mem_read(0x83b0e4,4));oldflag=bytes(cpu.mem_read(0xa55498,4))
 cpu.mem_write(0x83b0e4,struct.pack('<I',0x7000e100));cpu.mem_write(0x7000e100,b'\xc2\x04\x00')
 hook=cpu.hook_add(UC_HOOK_CODE,observe,begin=0x7000e100,end=0x7000e100)
 try:
  for mode,entry in enumerate((0x533f60,0x530a90,0x5354d0)):
   for seed in range(512):
    value=seed if seed<256 else ((seed*0x1020305)^0x87654321)&0xffffffff
    for api in ((0,1,4,5,6,0xffffffff,0x80000005,0x10000005) if mode==0 else (0,)):
     drive.clear();cpu.mem_write(0xa55498,struct.pack('<I',value))
     oracle.call(entry,() if mode==2 else (value,),instruction_limit=20000)
     out=[cpu.reg_read(oracle.reg.UC_X86_REG_EAX),*drive]
     cases.append(dict(input=[mode,value,api],output=out))
 finally:
  cpu.hook_del(hook);cpu.mem_write(0x83b0e4,saved);cpu.mem_write(0xa55498,oldflag)
 return cases
