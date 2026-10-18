"""Complete original pop/peek calls with actual scan translation and scripted state acquisition."""
import struct
from tools.input_queue_cases import BASE,SIZE,QueueOracle,fixture,put,words
from tools.input_translation_cases import TranslationOracle


def event(f,index,scan,character,extended=1):
    address=(BASE+0x428+(index&0xffffffff)*4)&0xffffffff
    offset=address-BASE
    if not 0<=offset<=SIZE-4:raise ValueError('fixture event outside mapped image')
    put(f['globals'],offset,((character&65535)<<16)|((scan&255)<<8)|(extended&255))


def make(capacity,head,tail,kind,seed=0):
    f=fixture(seed,capacity,seed&1)
    put(f['globals'],4,head);put(f['globals'],0x4e0,tail)
    config=[17,0,0,128,(0,1,0xffffffff)[seed%3],0,0,seed&255,65,1,1]
    for i in range(32):
        scan=17+i;character=65+i
        if kind in (2,3,4):scan=17;character=0
        if kind in (1,7):scan=0x3a;character=0 if kind==7 else 66
        if kind==5:scan=1;character=0
        if kind==6:character=0xffff if i&1 else 0x8000
        event(f,i,scan,character,255 if i&1 else 0)
    if kind==1 and head<32:event(f,head,0x3a,0)
    if kind==2:
        for i in range(32):event(f,i,17,66)
        if head<32:event(f,head,17,0)
    if kind in (2,3):config[8]=0
    if kind==4:config[8]=(128,143,144,255)[seed%4]
    if kind==5:config[0]=1;config[2]=4;config[5]=1
    if kind in (1,7):config[6]=(0,1,2,4,8)[seed%5]
    return f,config


def fixtures(name):
    positions={0:((0,0),),1:((0,0),),2:((0,0),(0,1),(1,0)),
               4:((0,0),(0,1),(0,3),(3,1),(2,0)),32:((0,0),(0,1),(31,0),(29,1),(0,31))}
    seed=0
    for capacity,pairs in positions.items():
        for head,tail in pairs:
            for kind in range(8):
                f,config=make(capacity,head,tail,kind,seed)
                yield 0,0,config,f;seed+=1
    for mask in (1,2,4,8,16,32,63):
        f,config=make(4,0,1,0,seed);f['mask']=mask;f['value']=1
        yield 0,0,config,f;seed+=1
    for mask in (1,2,4,8,16,31):
        f,config=make(4,0,1,1 if mask&8 else 4,seed);config[8]=65
        yield mask,2 if mask==8 else 1,config,f;seed+=1
    for head in (0xffffffff,0x40000000,0xfffffef7,0x40000020):
        f,config=make(4,head,0,0,seed);config[7]=73;config[4]=0
        if head==0xfffffef7:put(f['globals'],4,head) # Self-alias: event is the cursor word itself.
        elif head!=0x40000020:event(f,head,17,65)
        yield 0,0,config,f;seed+=1
    if name=='input_queue_peek':
        f,config=make(0,0,1,0,seed)
        yield 0,0,config,f # No division occurs when retaining a stored character.


def capture(oracle,name):
    queue=QueueOracle(oracle);script={}
    def mutate(observer):
        if observer.get_calls!=1:return
        mask,value=script['mask'],script['value']
        if mask&1:queue.put(4,value)
        if mask&2:queue.put(0x4a8,2)
        if mask&4:queue.put(0x520,value^0x11223344)
        if mask&8:queue.put(0x4e0,value&31)
        if mask&16:queue.put(0x428,0xffff5501)
    translation=TranslationOracle(oracle,mutate);result=[]
    with queue.substituted(),translation.substituted():
        for mask,value,config,f in fixtures(name):
            script.update(mask=mask,value=value);queue.reset(f);translation.reset(config)
            oracle.call(0x5830c0 if name=='input_queue_pop' else 0x583160,instruction_limit=100000)
            result.append(dict(input=[mask,value,*config,*words(f)],
                output=[int(translation.exited),0 if translation.exited else oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX),
                        *queue.output(),*translation.output(True)]))
    return result
