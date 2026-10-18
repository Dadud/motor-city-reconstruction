"""Full startup with actual mouse runtime bodies and shared observed globals."""
from tools.startup_initialize_cases import StartupOracle, DIAG0
from tools.input_mouse_runtime_cases import (RuntimeOracle, FIELDS, QUERY, CTOR,
    CONTEXT, DTOR, GATE, DIAG, BINDINGS)
from tools.input_mouse_callbacks_cases import EXTRA
from tools.cleanup_registry_cases import BASE
from tools.startup_toggle_cases import ToggleOracle
from tools.input_toggle_key_cases import EVENT, SECOND

STEPS = ((0,0,0,0),(1,7,5,0),(2,0xff880000,7,0),(6,400,300,0),
         (7,90,100,0),(3,0,0,0),(0,0,0,0),(9,0,0,0),
         (4,800,600,0),(0,0,0,0),(5,0,0,0),(0,0,0,0),
         (1,0,17,0),(3,0,0,0),(8,0,0,0),(0,0,0,0),
         (2,120<<16,7,0),(10,0,0,0),(11,0,0,0),(3,0,0,0),(3,0,0,0))


def lifecycle_cases(oracle):
    from unicorn import UC_HOOK_CODE
    cpu = oracle.cpu
    mouse, startup, toggle = RuntimeOracle(oracle), StartupOracle(oracle), ToggleOracle(oracle)
    cases = []
    helpers = (QUERY, CTOR, CONTEXT, DTOR)
    saved = {a: bytes(cpu.mem_read(a, 3)) for a in helpers}
    pointers = [iat for iat, _, _ in BINDINGS] + [0x8c4938]
    pointer_values = [mouse.word(a) for a in pointers]
    for iat, stub, cleanup in BINDINGS:
        mouse.put(iat, stub)
        cpu.mem_write(stub, b'\xc2' + cleanup.to_bytes(2, 'little'))
    for a in (*helpers, GATE, DIAG):
        cpu.mem_write(a, b'\xc3')
    mouse.put(0x8c4938, GATE)
    hooks = [cpu.hook_add(UC_HOOK_CODE, mouse.api, begin=a, end=a)
             for a in (*helpers, GATE, DIAG, *[s for _, s, _ in BINDINGS])]
    try:
        with mouse.substituted(real_helpers=(0x6f06c0,0x582e40,0x6efaf0,0x6f0720,0x6bf450,0x584cf0)), startup.substituted(real_numlock=True,real_helpers=(0x6ef890,)), toggle.substituted():
            for seed, (profile, script) in enumerate(((0,0),(1,0),(3,4),(4,8),(5,1),(6,1),(7,128),(0,12))):
                for variant in range(4):
                    values = [0]*17
                    values[15:17] = [640,480]
                    mouse.reset([0,profile,script,seed], values)
                    for a in EXTRA:
                        mouse.put(a, 0)
                    for a in FIELDS[-6:]:
                        mouse.put(a, 0)
                    config = [0 if variant in (0,3) else 512|2048 if variant==1 else 128,
                              0, 0 if variant==2 else 1, 0 if variant==2 else 1,
                              0 if variant==2 else 1, seed]
                    globals = [DIAG0,0x1234,0x5678,1 if variant in (1,3) else 0,
                               1,0x7777,0,0xa5,0,640,480,32,1,2,0]
                    startup.reset(config, globals)
                    mouse.put(0xb3656c,0)
                    toggle.reset([(0,1,0xffff,0x8000)[variant],(seed&3)|4])
                    cpu.mem_write(0xaca8f0, bytes(0x530))
                    mouse.put(0xacadb0,7);mouse.put(0xacadb4,7);mouse.put(0xacae14,0x12345678)
                    mouse.put(0x89bdd4,1);mouse.put(0x8c4938,GATE)
                    slots = [0x6efad0]*64 if variant==3 else [0]*64
                    for i, value in enumerate(slots):
                        mouse.put(BASE+i*4,value)
                    output=[]
                    for op,a,b,c in STEPS:
                        result=0
                        if op==0:oracle.call(0x6bfa10,(),instruction_limit=100000)
                        elif op==1:
                            oracle.call(0x6efaf0,(a,b));result=cpu.reg_read(oracle.reg.UC_X86_REG_EAX)&255
                        elif op==2:
                            oracle.call(0x583210,(b,0x20a,a,0,0),instruction_limit=100000)
                            result=cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
                        elif op==3:oracle.call(0x6bf410,(),instruction_limit=100000)
                        elif op==4:startup.put(0x8c4618,a);startup.put(0x8c461c,b)
                        elif op==5:startup.put(0x8c45f8,a)
                        elif op==6:oracle.call(0x6effd0,(0,0,0,a,b,500),instruction_limit=100000)
                        elif op==7:oracle.call(0x6f07f0,(a,b),instruction_limit=100000)
                        elif op==8:oracle.call(0x6bf450,(0x6efad0,))
                        elif op==9:
                            oracle.call(0x6f0670);result=cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
                        elif op in (10,11):oracle.call(0x6f06a0 if op==10 else 0x6f06b0)
                        output.extend([result,*startup.output(),*mouse.output(0)])
                        output.extend([toggle.state,int(toggle.word(EVENT)==SECOND),len(toggle.logs),
                                       *(v for row in toggle.logs for v in row[:6])])
                        mouse.events.clear()
                    cases.append(dict(input=[profile,script,seed,variant,*config,*globals,len(STEPS),
                                             *(v for step in STEPS for v in step)],output=output))
    finally:
        for hook in hooks:
            cpu.hook_del(hook)
        for address, data in saved.items():
            cpu.mem_write(address,data)
        for address, value in zip(pointers,pointer_values):
            mouse.put(address,value)
        if hasattr(cpu,'ctl_flush_tb'):
            cpu.ctl_flush_tb()
    return dict(cases=cases,scope='Full actual startup with actual Num Lock wrapper/setter, mouse initialization, runtime state/geometry, wheel dispatch, reporting, cleanup registry and mouse shutdown. Width/height, diagnostic words, window image and registry are shared. Keyboard initialization and other startup/COM/cursor/context/key APIs remain declared returning boundaries; key-state observations are fixed and synthetic factories fully write output slots. Void results normalized; no live game or Windows API claim.')
