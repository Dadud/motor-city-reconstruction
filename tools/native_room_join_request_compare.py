"""Compare native room request construction with original-verified Python.

Uses synthetic object fields and inert owner tokens; no sockets or host calls.
"""
import argparse
import json
from pathlib import Path
import random
import struct
import subprocess

from client.room_join_request import RoomJoinInputs, build_room_join_argument


def verify(runner):
    runner = str(Path(runner).resolve())
    rng = random.Random(0x44cf80)
    matched = rejected = malformed = 0
    cases = []
    for length in (0,1,29,30,31):
        for password in (b'',b'p',b'p' * 16):
            for flag in (False,True):
                for wait in (False,True):
                    image = bytearray(rng.randbytes(0x3b8))
                    image[0xa0:0xc0] = b'n' * length + bytes(32 - length)
                    cases.append((bytes(image),password,flag,wait,rng.getrandbits(32) if wait else None))
    image = bytearray(0x3b8)
    for password in (b'x' * 17,b'a\0b'):
        cases.append((bytes(image),password,False,False,None))
    cases.extend(((bytes(image),b'',False,True,None),(bytes(image),b'',False,False,1)))
    image[0xa0:0xc0] = b'x' * 32
    cases.append((bytes(image),b'',False,False,None))
    for image,password,flag,wait,owner in cases:
        raw = image + bytes((int(flag),int(wait),int(owner is not None)))
        raw += struct.pack('<IB',owner or 0,len(password)) + password
        try:
            expected = build_room_join_argument(RoomJoinInputs.from_room_image(image),
                password=password,flag_0x20=flag,wait_for_completion=wait,owner_token=owner)
        except ValueError:
            expected = None
        result = subprocess.run([runner],input=raw,capture_output=True,timeout=10)
        if expected is None:
            if result.returncode != 1 or result.stdout: raise AssertionError('native accepted invalid request inputs')
            rejected += 1
        elif result.returncode or result.stdout != expected:
            raise AssertionError('native request differs from original-verified Python')
        else: matched += 1
    for raw in (b'',bytes(0x3bf),bytes(0x3c1)):
        result = subprocess.run([runner],input=raw,capture_output=True,timeout=10)
        if result.returncode != 2 or result.stdout: raise AssertionError('native runner accepted malformed input')
        malformed += 1
    return {'matched_arguments':matched,'matched_rejections':rejected,'malformed_inputs_rejected':malformed,
            'original_binary_executed':False,'live_server_tested':False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner),indent=2))
