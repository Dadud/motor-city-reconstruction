"""Synthetic raw-key and latch observations from complete original bodies."""
import random
RAW=0x8c8648
LATCHES=0x9e1be8


def pattern(size,seed):
    return bytes((seed+k*37)&255 for k in range(size))


def eax(oracle):
    return oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)


def capture(oracle,name,entry):
    result=[]
    if name=='input_key_release':
        rows=[(scan,kind,1,True) for scan in range(128) for kind in range(5)]
        rows += [(scan,kind,enabled,matched) for scan in (0,42,54,127)
                 for kind in (0,3) for enabled in (0,1,0x80000000) for matched in (False,True)]
        for scan,kind,enabled,matched in rows:
            remap=bytes(k if kind==0 else 127-k if kind==1 else k+128 if kind==2
                        else 42 if kind==3 else 54 for k in range(128))
            keys=pattern(256,17);target=0x12345678;window=target if matched else 0x87654321
            bits=(scan<<16)|0x81000001
            oracle.cpu.mem_write(RAW,keys);oracle.cpu.mem_write(oracle.inputs,remap)
            oracle.cpu.mem_write(0xacae18,(oracle.inputs if kind else 0).to_bytes(4,'little'))
            oracle.cpu.mem_write(0xacadb0,target.to_bytes(4,'little'))
            oracle.call(entry,(enabled,window,0xabcdef01,0x76543210,bits,0xdeadbeef),cleanup=b'')
            result.append(dict(input=[int(kind!=0),enabled,window,target,bits,*keys,*remap],
                output=[eax(oracle),*list(oracle.cpu.mem_read(RAW,256)),
                        *list(oracle.cpu.mem_read(oracle.inputs,128))]))
        return result
    if name=='input_key_raw':
        for seed in (0,1,128,255):
            keys=pattern(128,seed)
            oracle.cpu.mem_write(RAW,keys)
            for code in (*range(512),0x7fffffff,0x80000000,0x80000001,
                         0xffffff7f,0xffffff80,0xfffffffe,0xffffffff):
                oracle.call(entry,(code,))
                result.append(dict(input=[code,*keys],output=[eax(oracle),*list(oracle.cpu.mem_read(RAW,128))]))
        for value in range(256):
            keys=bytearray(pattern(128,7));keys[0]=value
            oracle.cpu.mem_write(RAW,bytes(keys));oracle.call(entry,(0,))
            result.append(dict(input=[0,*keys],output=[eax(oracle),*list(oracle.cpu.mem_read(RAW,128))]))
        rng=random.Random(0x460670)
        for _ in range(64):
            code=rng.getrandbits(32);keys=bytes(rng.getrandbits(8) for _ in range(128))
            oracle.cpu.mem_write(RAW,keys);oracle.call(entry,(code,))
            result.append(dict(input=[code,*keys],output=[eax(oracle),*list(oracle.cpu.mem_read(RAW,128))]))
        return result
    if name!='input_key_query': raise ValueError(name)
    rows=[]
    for code in (0,1,29,56,127,128,129,157,255,256,257,511):
        for raw in (0,1,128,255):
            for latch in (0,1,2,128,255):
                for mode in (0,1,256,0x80000000): rows.append((code,raw,latch,mode))
    rows += [(code,(code*37)&255,(code*11)&255,code%2) for code in range(512)]
    for code,raw,latch,mode in rows:
        keys=bytearray(pattern(128,13));keys[code&127]=raw
        latches=bytearray(pattern(512,29));latches[code]=latch
        oracle.cpu.mem_write(RAW,bytes(keys));oracle.cpu.mem_write(LATCHES,bytes(latches))
        oracle.call(entry,(code,mode))
        result.append(dict(input=[code,mode,*keys,*latches],output=[eax(oracle),
            *list(oracle.cpu.mem_read(RAW,128)),*list(oracle.cpu.mem_read(LATCHES,512))]))
    return result


def lifecycle_cases(oracle):
    result=[]
    steps=[(1,128,1),(1,128,1),(1,1,1),(129,1,1),(1,0,0),(129,0,1),
           (1,255,0),(1,255,256),(1,255,1),(1,0,1),(1,2,0x80000000),
           (257,255,1),(257,0,0),(255,128,1),(127,128,1),(255,0,1),
           (42,1,1),(54,1,1),(42,0,1),(54,0,1),(42,1,1)]
    for seed in (0,0xa5):
        for variant in range(3):
            keys=pattern(128,seed);latches=pattern(512,seed^0x55)
            sequence=steps if variant==0 else list(reversed(steps)) if variant==1 else steps+steps
            oracle.cpu.mem_write(RAW,keys);oracle.cpu.mem_write(LATCHES,latches)
            oracle.cpu.mem_write(0xacae18,b'\0'*4)
            oracle.cpu.mem_write(0xacadb0,(7).to_bytes(4,'little'))
            output=[]
            for code,raw,mode in sequence:
                if raw==0:
                    oracle.call(0x584610,(1,7,0xabcdef01,0x76543210,(code&127)<<16,0xdeadbeef),cleanup=b'')
                else:
                    oracle.cpu.mem_write(RAW+(code&127),bytes([raw]))
                oracle.call(0x4acdc0,(code,mode))
                output += [eax(oracle),*list(oracle.cpu.mem_read(RAW,128)),
                           *list(oracle.cpu.mem_read(LATCHES,512))]
            result.append(dict(input=[*keys,*latches,len(sequence),
                *(v for step in sequence for v in step)],output=output))
    return dict(scope='connected complete key-query and release calls; actual raw-key child; no substitutions',cases=result)
