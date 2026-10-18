"""Persistent original initialization, acquisition, queue and teardown paths."""
import struct
from contextlib import contextmanager
from tools.input_device_lifetime_cases import LifetimeOracle,make,OBJECT,TABLE,STUB,GLOBAL
from tools.input_queue_cases import words,put as image_put
from tools.input_translation_cases import TranslationOracle,TABLES
KEYBOARD=0xb36460
ACQUISITION=(0x64,0x1c,0x24)
class SessionOracle(LifetimeOracle):
    def reset_session(self,config,state,queue,acquisition,translation):
        TranslationOracle(self.oracle).reset(translation)
        super().reset(config,state,queue)
        self.acquisition=acquisition;self.acquisition_logs=[];self.counts=[0,0,0]
        self.put(KEYBOARD,0x12345678)
        self.oracle.cpu.mem_write(KEYBOARD+4,bytes((acquisition[6]+i*13)&255 for i in range(256)))
        for index in (2,3):
            for table in (0,1):
                for method in ACQUISITION:
                    stub=STUB+index*0x400+table*0x100+method
                    self.put(TABLE+index*0x200+table*0x100+method,stub)
                    self.oracle.cpu.mem_write(stub,b'\xc2'+struct.pack('<H',12 if method==0x24 else 4))
    def observe(self,cpu,address,size,user):
        if not STUB<=address<STUB+0x1800 or (address-STUB)%0x100 not in ACQUISITION:
            return super().observe(cpu,address,size,user)
        relative=address-STUB;index=relative//0x400;table=(relative%0x400)//0x100;method=relative%0x100
        stack=cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP)
        identity=self.word(stack+4);requested=self.word(stack+8) if method==0x24 else 0
        if identity!=OBJECT+index*0x100 or index not in (2,3):raise AssertionError('session device identity')
        if method==0x24 and (requested!=256 or self.word(stack+12)!=KEYBOARD+4):raise AssertionError('session keyboard read ABI')
        self.acquisition_logs.append([method,index,table,identity,requested,*cpu.mem_read(KEYBOARD,260),*(self.word(a) for a in GLOBAL)])
        kind=ACQUISITION.index(method);self.counts[kind]+=1
        status=self.acquisition[kind*2+min(self.counts[kind]-1,1)]
        if method==0x24:
            seed=self.acquisition[6];n=len(self.acquisition_logs)
            cpu.mem_write(KEYBOARD+4,bytes((seed+n*37+i)&255 for i in range(requested)))
        if self.acquisition[7]&1:self.put(identity,TABLE+index*0x200+(1-table)*0x100)
        cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX,status)
    def session_output(self):
        cpu=self.oracle.cpu
        return [*self.output(),*cpu.mem_read(KEYBOARD,260),self.word(0x8c8644),self.word(0x8c8640),*cpu.mem_read(TABLES,620),len(self.acquisition_logs),*(v for row in self.acquisition_logs for v in row)]
    @contextmanager
    def session_substituted(self):
        from unicorn import UC_HOOK_CODE
        addresses=[STUB+i*0x400+t*0x100+m for i in (2,3) for t in (0,1) for m in ACQUISITION]
        hooks=[self.oracle.cpu.hook_add(UC_HOOK_CODE,self.observe,begin=a,end=a) for a in addresses]
        try:
            with self.substituted(),self.queue.substituted():yield
        finally:
            for hook in hooks:self.oracle.cpu.hook_del(hook)
def lifecycle_cases(oracle):
    observer=SessionOracle(oracle);cases=[];audits=[]
    with observer.session_substituted():
        for variant in range(8):
            profile=variant%4;callback_alias=variant>=4
            config,state,queue=make(4,0,0,4 if profile==3 else 0,196 if profile==2 else 4,73,initialized=int(profile in (1,2)))
            image_put(queue['globals'],4,0);image_put(queue['globals'],0x4e0,0)
            acquisition=[0,0,0,0,0,0,73,1]
            if profile==1:acquisition[4]=1;acquisition[5]=1
            if profile==2:acquisition[0]=0x8007001e;acquisition[4]=0x8007000c
            translation=[17,0,0,128,0,0,0,73,65,1,1]
            observer.reset_session(config,state,queue,acquisition,translation)
            steps=[(0,0,0,0,0,0),(1,6,0,0,0,0),(0,0,0,0,0,0)]
            if profile!=3:
                steps.extend([(4,1,7,0x100,0x41,1|(58<<16)),(4,1,7,0x100,0x41,1|(17<<16)),
                              (5,1,7,0x102,0x8000,1),(6,0,0,0,0,0),(6,0,0,0,0,0),
                              (7,0,0,0,0,0),(7,0,0,0,0,0),(7,0,0,0,0,0),(8,17,0,0,0,0)])
            if callback_alias:
                for callback in (0x81807f41,0x00ff908f,0xffff0000,0x01020304):
                    steps.append((9,10,callback,0,0,0))
                    if profile!=3:steps.extend((8,scan,0,0,0,0) for scan in range(112,116))
            steps.extend([(2,0,0,0,0,0),(1,6,0,0,0,0),(3,0,0,0,0,0),(1,6,0,0,0,0),
                          (0,0,0,0,0,0),(1,6,0,0,0,0)])
            if profile!=3:steps.append((8,17,0,0,0,0))
            steps.extend([(2,0,0,0,0,0),(1,6,0,0,0,0)])
            output=[];observations=[]
            for op,a,b,c,d,e in steps:
                before_acquisition=len(observer.acquisition_logs)
                observer.temporary=0;oracle.cpu.reg_write(oracle.reg.UC_X86_REG_ECX,config[3])
                entry={0:0x6f0200,1:0x6f03c0,2:0x6f0310,3:0x6f0350,4:0x584450,5:0x584370,6:0x583160,7:0x5830c0,8:0x6f05b0,9:0x6f0360}[op]
                args=(a,) if op==1 else ((a,b,c,d,e,0xdeadbeef) if op in (4,5) else ((a,b) if op in (8,9) else ()))
                oracle.call(entry,args,cleanup=b'' if op in (4,5) else None,instruction_limit=100000)
                result=0 if op in (2,3) else oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
                output.extend([result,*observer.session_output()])
                interface=observer.word(GLOBAL[0]);device=observer.word(GLOBAL[1])
                if op==1:
                    if interface==0 and (result!=0 or len(observer.acquisition_logs)!=before_acquisition):
                        raise AssertionError('disabled original read called device or returned image')
                    if interface!=0 and (result!=KEYBOARD or len(observer.acquisition_logs)<=before_acquisition):
                        raise AssertionError('enabled original read did not execute acquisition')
                observations.append(dict(operation=op,arguments=[a,b,c,d,e],result=result,interface=interface,device=device,callback=observer.word(GLOBAL[4]),
                    initialized=observer.word(GLOBAL[2]),acquisition_calls=len(observer.acquisition_logs),
                    queue_head=observer.queue.word(4),queue_tail=observer.queue.word(0x4e0),caps=observer.word(0x8c8644)))
            audits.append(dict(profile=profile,callback_alias=callback_alias,steps=observations))
            cases.append(dict(input=[*config,*state,*words(queue),*acquisition,*translation,len(steps),*(v for step in steps for v in step)],output=output))
    return dict(cases=cases,audit=audits,scope='Persistent actual initialization, device acquisition/retry/clear, producers, translation, queue consumers, cleanup, shutdown and reads after teardown; only platform methods and lock imports substituted. Void teardown results normalized to zero.')
