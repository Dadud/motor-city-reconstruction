"""Original complete camera cycle/mode bodies; only record handlers substituted."""
import struct
from tools.record_machine_cases import BASE, RECORDS, CURRENT, NONE, machine, pack, pair_image, scripts
from tools.selection_controller_cases import SelectionOracle, fixture_words
SUBJECTS=0x98c370


def base(seed=0,script=None):
    f=machine(seed,1,3,script or (NONE,NONE,0,0))
    f.update(mode=0,presets=[2,3,4],modes=list(range(9)),context=[0,9,0],counters=[7,11])
    return f


def observations():
    return (*scripts(),(NONE,BASE+8,19,0x11223344),(NONE,BASE+12,19,0x11223344))


def mode_fixtures():
    for k,target in enumerate((*range(32),0x80000000,NONE)):
        contexts=([0,9,0],[18,9,0],[0,9,24]) if target==23 else ([0,9,0],)
        for mode in (0,255):
            for context in contexts:
                for script in observations():
                    index=k%9
                    f=base(k*7,script);f['mode']=mode;f['modes'][index]=target;f['context']=context
                    wanted=(8 if mode==0 else 12) if target==23 else target
                    for matched in (False,True):
                        yield index,f,pair_image([(15,wanted)] if matched else [])
    for index in (9,10,0x7fffffff):
        f=base();pack(f['image'],CURRENT,0)
        yield index,f,pair_image([])


def cycle_fixtures():
    k=0
    for old in (*range(32),0x80000000,NONE):
        for mode in (0,255):
            for script in scripts()[:3]:
                f=base(k*7,script);f['mode']=mode;f['modes'][0]=23
                pack(f['image'],RECORDS+256+4,old);pack(f['image'],0x760,0)
                for matched in (False,True):
                    yield old==10 and NONE or k%15,True,f,pair_image([(old,5),(old,12)] if matched else [])
                k+=1
    patterns=((1,2,3,4),(0,0,0,0),(1,0,0,0),(1,NONE,0,0),(1,0,2,0),
              (0x80000000,0,0,0),(0x7fffffff,0,0,0),(1,5,6,0xfffffffa))
    for p,values in enumerate(patterns):
        for slot in (0,1,3,NONE):
            for mode in (0,255):
                for script in observations():
                    f=base(k*11,script);f['count']=values[0];f['presets']=list(values[1:])
                    f['pending']=slot;f['index']=NONE;f['mode']=mode;f['modes'][0]=23
                    pack(f['image'],RECORDS+256+4,4)
                    pack(f['image'],0x760,9 if p==7 else 0)
                    for matched in (False,True):
                        yield k%15,True,f,pair_image([(4,4),(4,5),(4,6),(4,7),(4,12)] if matched else [])
                    k+=1
    for old in (24,10,11,27,4):
        for index in (*range(9),NONE,0x7ffffffe):
            for mode in (0,255):
                for script in observations():
                    f=base(k*13,script);f['mode']=mode
                    f['modes']=[4]*9;f['modes'][k%9]=(23,14,24,29,15,0,17)[k%7]
                    pack(f['image'],RECORDS+256+4,old);pack(f['image'],0x760,index)
                    for matched in (False,True):
                        # Cover every possible selected result without computing outputs.
                        yield (NONE if old==10 else k%15),False,f,pair_image(
                            [(old,v) for v in (8,12,14,24,29,15,0)] if matched else [])
                    k+=1


def capture(oracle,name,entry):
    result=[];observer=SelectionOracle(oracle)
    with observer.substituted():
        if name=='record_mode_apply':
            for index,f,pairs in mode_fixtures():
                observer.reset(f);oracle.cpu.mem_write(0x88acdc,bytes(pairs))
                oracle.call(entry,(index,))
                result.append(dict(input=[index,*fixture_words(f,pairs)],output=observer.output()))
        elif name=='record_selection_cycle':
            for viewport,equal,f,pairs in cycle_fixtures():
                table=bytearray((k*37+11)&255 for k in range(120))
                if viewport!=NONE:
                    pack(table,viewport*4,0x12345678)
                    pack(table,0x3c+viewport*4,0x12345678 if equal else NONE)
                observer.reset(f);oracle.cpu.mem_write(0x88acdc,bytes(pairs))
                oracle.cpu.mem_write(SUBJECTS,bytes(table));oracle.call(entry,(viewport,))
                result.append(dict(input=[viewport,*table,*fixture_words(f,pairs)],
                    output=[*observer.output(),*list(oracle.cpu.mem_read(SUBJECTS,120))]))
        else: raise ValueError(name)
    return result


def lifecycle_cases(oracle):
    """Six complete calls with preset and subject changes between cycles."""
    result=[];observer=SelectionOracle(oracle)
    with observer.substituted():
        for seed in (0,0xa5):
            for script in ((NONE,NONE,0,0),(NONE,NONE,16,42)):
                for matched in (False,True):
                    f=base(seed,script);f['context']=[18,9,0]
                    f['modes']=[23,4,14,23,4,4,4,4,4]
                    pairs=pair_image([(24,6),(6,5),(5,12),(12,14),(14,12)] if matched else [])
                    table=bytearray(120);pack(table,4,0x12345678);pack(table,0x40,0x12345678)
                    observer.reset(f);oracle.cpu.mem_write(0x88acdc,bytes(pairs))
                    oracle.cpu.mem_write(SUBJECTS,bytes(table))
                    oracle.call(0x434e40)
                    oracle.call(0x436c90)
                    oracle.call(0x436520,(1,))
                    observer.put(BASE+0x760,0)
                    oracle.cpu.mem_write(0xaa459c,b'\xff')
                    oracle.call(0x436fa0,(0,))
                    observer.put(SUBJECTS+0x40,NONE)
                    oracle.call(0x436520,(1,))
                    oracle.call(0x436520,(1,))
                    if len(observer.logs)!=11:
                        raise AssertionError('camera cycle lifecycle callback count changed')
                    result.append(dict(input=[1,*table,*fixture_words(f,pairs)],
                        output=[*observer.output(),*list(oracle.cpu.mem_read(SUBJECTS,120))]))
    return dict(scope='six complete calls: initialize, select, preset cycle, explicit mode, two subject cycles; callbacks explicitly substituted',cases=result)
