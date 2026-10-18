"""Complete original input initializer including actual registration/sort calls."""
import random


def fixtures():
    rng=random.Random(0x583c30)
    for count in (0,1,8,100,127,128):
        for kind in range(3):
            keys=[0x100+i*3 for i in range(count)]
            if kind==1:keys.reverse()
            if kind==2:keys=[rng.getrandbits(32) for _ in range(count)]
            for flag in (0,1,0x80000000):
                yield keys,0x100,0,0,flag,0 if kind&1 else 0x12345678,0 if count&1 else 0x87654321,0 if kind==0 else 0x100
    for count in (0,28,128):
        keys=[0x1000+i for i in range(count)]
        for mask in (1,2,4,8,32,256,263):
            yield keys,0x100,0,mask,0,0,0,0


def capture(oracle):
    from tools.window_registration_cases import capture as capture_registration
    return capture_registration(oracle,True)
