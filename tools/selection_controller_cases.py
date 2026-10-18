"""Complete camera selection controller calls with explicit handler substitutions."""
import struct
from tools.record_machine_cases import (MachineOracle, BASE, SIZE, RECORDS, CURRENT,
    NONE, HANDLERS, machine, pack, pair_image, input_words, scripts)

PRESETS = (0x9aba9c, 0x9abaa0, 0x9abaa4)
COUNTERS = (0x88ac30, 0x88ac34)
MODES, CONTEXT, MODE = 0x88ac50, 0x9aa9b0, 0xaa459c


def fixtures():
    variants = [(*script,) for script in scripts()]
    variants += [(NONE, BASE+shift, 19, 0x11223344) for shift in (0,4,8,12)]
    values = (0,1,4,5,6,0x7fffffff,0x80000000,NONE)
    for index, value in enumerate(values):
        for script in variants:
            f = machine(index*19, 1, value, script)
            f.update(mode=0, presets=[value, value ^ 0x12345678, (value+3)&NONE],
                     modes=list(range(9)), context=[0,0x1234,0], counters=[7,11])
            f['index'] = value; f['pending'] = value
            target = (0 if value & 0x80000000 else value) % 5 + 4
            for match in (False, True):
                yield f, pair_image([(15,target)] if match else [])
    targets = (*range(32),0x80000000,NONE)
    for k, target in enumerate(targets):
        for context in ([0,0x1234,0],[18,9,0],[0,9,23],[0,9,24],[0,9,25]):
            if target != 23 and context[2] != 0: continue
            for script in variants:
                f = machine(k*7, 1, 0x80000000, script)
                slot = k % 9
                modes = list(range(9)); modes[slot] = target
                f.update(mode=(1,255)[k%2], presets=[NONE,7,0x80000000],
                         modes=modes, context=context, counters=[7,11])
                pack(f['image'],0x760,slot)
                wanted = 12 if target == 23 else target
                for match in (False,True):
                    yield f, pair_image([(wanted,15)] if match else [])
    for index in (9,10,0x7fffffff):
        f = machine(13,1)
        f.update(mode=1,presets=[2,3,4],modes=list(range(9)),context=[18,9,24],counters=[7,11])
        pack(f['image'],0x760,index); pack(f['image'],CURRENT,0)
        yield f, pair_image([])


def fixture_words(f,pairs):
    return [f['mode'], *struct.pack('<9I',*f['modes']),
            *struct.pack('<3I',*f['context']), *pairs, *f['presets'],
            *f['counters'], *input_words(f)]


class SelectionOracle(MachineOracle):
    def reset(self, fixture):
        super().reset(fixture)
        for address,value in zip((*PRESETS,*COUNTERS),(*fixture['presets'],*fixture['counters'])):
            self.put(address,value)
        self.oracle.cpu.mem_write(MODES,struct.pack('<9I',*fixture['modes']))
        self.oracle.cpu.mem_write(CONTEXT,struct.pack('<3I',*fixture['context']))
        self.oracle.cpu.mem_write(MODE,bytes([fixture['mode']]))
        self.extra_logs=[]

    def observe(self,cpu,address,size,user):
        if address not in HANDLERS: return
        self.extra_logs.append([self.word(a) for a in (*PRESETS,*COUNTERS)])
        super().observe(cpu,address,size,user)
        if self.script[2] & 16:
            for k,a in enumerate((*PRESETS,*COUNTERS)):
                self.put(a,self.script[3]+k)

    def output(self):
        result=[self.word(a) for a in (*PRESETS,*COUNTERS)]
        result+=super().output()
        for log in self.extra_logs: result.extend(log)
        result+=list(self.oracle.cpu.mem_read(MODES,36))
        result+=list(self.oracle.cpu.mem_read(CONTEXT,12))
        result+=list(self.oracle.cpu.mem_read(0x88acdc,64))
        return result


def capture(oracle,name,entry):
    if name == 'camera_context_special':
        result=[]
        for kind in (*range(32),0x80000000,NONE):
            for secondary in (0,18,22,23,24,25,NONE):
                data=struct.pack('<3I',kind,0xabcdef01,secondary)
                oracle.cpu.mem_write(oracle.inputs,data)
                oracle.call(entry,this_pointer=oracle.inputs)
                result.append(dict(input=list(data),output=[oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX),
                    *list(oracle.cpu.mem_read(oracle.inputs,12))]))
        return result
    result=[]
    observer=SelectionOracle(oracle)
    with observer.substituted():
        for f,pairs in fixtures():
            observer.reset(f)
            oracle.cpu.mem_write(0x88acdc,bytes(pairs))
            oracle.call(entry)
            result.append(dict(input=fixture_words(f,pairs),output=observer.output()))
    return result


def lifecycle_cases(oracle):
    """Four complete calls, including the initializer and repeated application."""
    result=[]
    observer=SelectionOracle(oracle)
    with observer.substituted():
        for seed in (0,0xa5):
            for script in ((NONE,NONE,0,0),(NONE,NONE,16,42),(NONE,NONE,20,7)):
                for matched in (False,True):
                    f=machine(seed,1,3,script)
                    f.update(mode=0,presets=[2,3,4],modes=[0,1,23,3,4,5,6,7,8],
                             context=[18,0x1234,0],counters=[7,11])
                    pairs=pair_image([(24,6),(6,12)] if matched else [])
                    observer.reset(f)
                    oracle.cpu.mem_write(0x88acdc,bytes(pairs))
                    oracle.call(0x434e40)
                    oracle.call(0x436c90)
                    observer.put(BASE+0x760,2)
                    oracle.cpu.mem_write(MODE,b'\x01')
                    oracle.call(0x436c90)
                    observer.put(BASE+0x760,9)
                    oracle.call(0x436c90)
                    if len(observer.logs)!=5:
                        raise AssertionError('selection lifecycle callback count changed')
                    result.append(dict(input=fixture_words(f,pairs),output=observer.output()))
    return dict(scope='connected complete calls: initialize, direct selection, special selection, disabled selection; callbacks explicitly substituted',cases=result)
