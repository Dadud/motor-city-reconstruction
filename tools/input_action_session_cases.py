"""Original full device sessions through the shipped default key action path."""
from tools.input_device_session_cases import SessionOracle,KEYBOARD
from tools.input_device_lifetime_cases import make,GLOBAL
from tools.input_queue_cases import words,put
from tools.input_default_key_cases import ActionOracle,image,DEFAULT
from tools.input_callback_dispatch_cases import DispatchOracle,ENABLED,CALLBACK,FIRST

def lifecycle_cases(oracle):
    session=SessionOracle(oracle);actions=ActionOracle(oracle);dispatch=DispatchOracle(oracle);cases=[];audit=[]
    with session.session_substituted(),actions.substituted(),dispatch.substituted():
        for profile in range(4):
            life,globals,queue=make(4,0,0,4 if profile==3 else 0,196 if profile==2 else 4,73,initialized=int(profile in (1,2)))
            put(queue['globals'],4,0);put(queue['globals'],0x4e0,0)
            acquisition=[0,0,0,0,0,0,73,1]
            if profile==1:acquisition[4]=1;acquisition[5]=1
            if profile==2:acquisition[0]=0x8007001e;acquisition[4]=0x8007000c
            translation=[17,0,0,128,0,0,0,73,65,1,1]
            control=[1,globals[4],0 if profile==3 else 1,1,0x12345680,0xabcdef02,0,73]
            script=(0,8,7,15)[profile];data=image(65,65,1)
            session.reset_session(life,globals,queue,acquisition,translation);dispatch.reset(control);actions.reset(script,data)
            steps=[(0,0,0,0,0,0),(1,6,0,0,0,0),(9,10,DEFAULT,0,0,0),(10,0,0,0,0,0),
                   (5,1,7,0x102,65,1),(10,0,0,0,0,0),
                   (4,1,7,0x100,0x41,1|(58<<16)),(4,1,7,0x100,0x41,1|(17<<16)),
                   (5,1,7,0x102,0x8000,1),(10,0,0,0,0,0),(10,0,0,0,0,0),(10,0,0,0,0,0),
                   (2,0,0,0,0,0),(1,6,0,0,0,0),(9,10,FIRST,0,0,0),(10,0,0,0,0,0),
                   (3,0,0,0,0,0),(1,6,0,0,0,0),(0,0,0,0,0,0),
                   (9,10,DEFAULT,0,0,0),(1,6,0,0,0,0),(5,1,7,0x102,65,1),(10,0,0,0,0,0),
                   (2,0,0,0,0,0),(1,6,0,0,0,0)]
            output=[];observations=[]
            for op,a,b,c,d,e in steps:
                before=len(session.acquisition_logs);session.temporary=0
                oracle.cpu.reg_write(oracle.reg.UC_X86_REG_ECX,life[3])
                entry={0:0x6f0200,1:0x6f03c0,2:0x6f0310,3:0x6f0350,4:0x584450,5:0x584370,9:0x6f0360,10:0x6f0450}[op]
                args=(a,) if op==1 else ((a,b,c,d,e,0xdeadbeef) if op in (4,5) else ((a,b) if op==9 else ()))
                oracle.call(entry,args,cleanup=b'' if op in (4,5) else None,instruction_limit=100000)
                result=0 if op in (2,3) else oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
                output.extend([result,*session.session_output(),*actions.output(),*dispatch.output()])
                interface=session.word(GLOBAL[0]);device=session.word(GLOBAL[1]);gate=session.word(ENABLED)
                if op==1:
                    if interface==0 and (result!=0 or len(session.acquisition_logs)!=before):raise AssertionError('disabled full-session acquisition')
                    if interface!=0 and (result!=KEYBOARD or len(session.acquisition_logs)<=before):raise AssertionError('missing full-session acquisition')
                observations.append(dict(operation=op,arguments=[a,b,c,d,e],result=result,interface=interface,device=device,gate=gate,callback=session.word(CALLBACK),
                    initialized=session.word(GLOBAL[2]),acquisition_calls=len(session.acquisition_logs),action_calls=len(actions.logs),
                    fallback_calls=len(dispatch.logs),head=session.queue.word(4),tail=session.queue.word(0x4e0)))
            audit.append(dict(profile=profile,steps=observations))
            cases.append(dict(input=[*life,*globals,*words(queue),*acquisition,*translation,*control,script,*data,len(steps),*(v for step in steps for v in step)],output=output))
    return dict(cases=cases,audit=audit,scope='Persistent actual initialization/acquisition/producer/dispatcher/default/pop/translation/action/teardown and reinitialization; only platform, action callbacks, and fallback helpers substituted. Void teardown normalized to zero.')
