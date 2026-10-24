"""Compare the 0x6f3090 wrapper with its real nested callbacks."""
import argparse
from pathlib import Path

from client.render_mode_dispatch import RenderDispatchState, dispatch_render_mode
from client.render_vertex_descriptor import query_render_vertex_descriptor
from tools.native_oracle import DynoOracle


VALUES=(0xaabb0001,0xaabb0002,0xaabb0003,0xaabb0004)


def model(input_word,mask,temporary_mode,previous_mode,mode_setting):
    cache=[previous_mode]; setting=[mode_setting]; counts=[0,0]
    def set_mode(value):
        old=setting[0];setting[0]=value
        if value==0: cache[0]=0xffffffff
        return old
    def dispatch(mode,count,source,scratch):
        primary=[0]*32;primary[8]=1
        secondary=[0]*8;secondary[2]=1
        state=RenderDispatchState(cached_mode=cache[0],capability_bit_4=1,
            capability_bit_2=1,capability_bit_0x10000=setting[0],
            capability_bit_0x20000_a=1,capability_bit_0x20000_b=1,
            capability_both_0x30000=1,capability_bit0=1,
            callback_context_b=0x31415926,vertex_stride=12,vertex_format=32,
            primary_callbacks=tuple(primary),secondary_callbacks=tuple(secondary),
            primary_callback=1,secondary_callback=1)
        _,updated,events=dispatch_render_mode(state,mode,count,source,0x2000)
        cache[0]=updated.cached_mode
        for event in events:
            if event[0]=='primary':
                counts[0]+=1;scratch[:]=VALUES
            elif event[0]=='secondary':counts[1]+=1
    outputs,_,_=query_render_vertex_descriptor(input_word,temporary_mode,mask,
        set_mode=set_mode,dispatch=dispatch)
    memory=tuple(outputs[i] if mask&(1<<i) else None for i in range(4))
    return memory,cache[0],setting[0],tuple(counts)


def verify(executable):
    oracle=DynoOracle(executable);cases=[]
    for temp in (0,0x20,0x100,0x20000):
        for previous in (0,8,0x1234,0x10008):
            for setting in (0,1):
                for mask in (0,1,5,15):
                    cases.append((0x71000100,mask,temp,previous,setting))
    for index,args in enumerate(cases):
        expected=model(*args)
        actual=oracle.render_vertex_descriptor(args[0],args[1],args[2],
                    previous_mode=args[3],mode_setting=args[4])
        if actual!=expected:
            raise AssertionError((index,args,actual,expected))
    return len(cases)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable',type=Path)
    args=parser.parse_args()
    print(f'0x6f3090 wrapper matches {verify(args.executable)} direct calls')
