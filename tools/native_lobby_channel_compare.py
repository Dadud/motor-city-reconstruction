"""Compare the native channel serializer against the original-verified Python codec."""
import argparse
import json
from pathlib import Path
import random
import subprocess

from client.lobby_channel_codec import ChannelJoinRecord, NATIVE_RECORD_SIZE


def verify(runner):
    rng = random.Random(106)
    matched = rejected = 0
    cases = []
    for first, second in ((0, 0), (1, 1), (31, 17), (30, 17), (15, 9)):
        for mode in range(9):
            raw = bytearray(rng.randbytes(NATIVE_RECORD_SIZE))
            if mode < 2:
                raw[:] = bytes([255 * mode]) * NATIVE_RECORD_SIZE
            raw[4:0x24] = b'n' * first + bytes(32 - first)
            raw[0x74:0x86] = b't' * second + bytes(18 - second)
            cases.append(bytes(raw))
    for _ in range(100):
        raw = bytearray(rng.randbytes(NATIVE_RECORD_SIZE))
        raw[4 + rng.randrange(32)] = 0
        raw[0x74 + rng.randrange(18)] = 0
        cases.append(bytes(raw))
    for start, end in ((4, 0x24), (0x74, 0x86)):
        raw = bytearray(NATIVE_RECORD_SIZE)
        raw[start:end] = b'x' * (end - start)
        cases.append(bytes(raw))
    for raw in cases:
        try:
            expected = ChannelJoinRecord(raw).payload()
        except ValueError:
            expected = None
        actual = subprocess.run([str(Path(runner).resolve())], input=raw,
                                capture_output=True, timeout=10)
        if expected is None:
            if actual.returncode != 1 or actual.stdout:
                raise AssertionError('native serializer accepted an invalid record')
            rejected += 1
        else:
            if actual.returncode != 0 or actual.stdout != expected:
                raise AssertionError('native serializer differs from verified Python codec')
            matched += 1
    for raw in (b'', bytes(NATIVE_RECORD_SIZE - 1), bytes(NATIVE_RECORD_SIZE + 1)):
        actual = subprocess.run([str(Path(runner).resolve())], input=raw,
                                capture_output=True, timeout=10)
        if actual.returncode != 2 or actual.stdout:
            raise AssertionError('native runner accepted invalid framing')
    return {'matched_payloads': matched, 'matched_rejections': rejected,
            'invalid_input_lengths_rejected': 3, 'live_server_tested': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner), indent=2))
