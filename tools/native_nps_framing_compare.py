"""Compare native plain NPS framing with the evidence-backed Python codec.

This synthetic corpus opens no socket and supplies no credentials.
"""
import argparse
import json
from pathlib import Path
import random
import struct
import subprocess

from client.nps_framing import Frame, FrameDecoder, MessageHeader, encode_message


def verify(runner):
    runner = str(Path(runner).resolve())
    counts = dict(serializations=0, stream_decodes=0, header_decodes=0, rejections=0)

    def compare(mode, data, action, category):
        try:
            expected = action()
        except ValueError:
            expected = None
        result = subprocess.run([runner, mode], input=data, capture_output=True, timeout=10)
        if expected is None:
            if result.returncode != 1 or result.stdout:
                raise AssertionError(f'native {mode} accepted malformed input')
            counts['rejections'] += 1
        elif result.returncode or result.stdout != expected:
            raise AssertionError(f'native {mode} differs from Python')
        else:
            counts[category] += 1

    rng = random.Random(0x7e0800)
    ids = (0, 1, 0x500, 0x501, 0x51a, 0x51b, 0x520, 0x521, 0x526, 0x527, 0x601, 0xffff)
    frames = []
    for message_id in ids:
        for size in (0, 1, 257, 65523, 65531, 65532):
            body = rng.randbytes(size)
            frame = Frame(message_id, body)
            compare('frame', struct.pack('>H', message_id) + body,
                    frame.encode, 'serializations')
            auxiliary = rng.getrandbits(32)
            compare('message', struct.pack('>HI', message_id, auxiliary) + body,
                    lambda: encode_message(message_id, body, auxiliary=auxiliary), 'serializations')
            if size <= 257:
                frames.append(frame)

    def decode(wire, chunk):
        decoder = FrameDecoder()
        frames = []
        for offset in range(0, len(wire), chunk):
            frames.extend(decoder.feed(wire[offset:offset + chunk]))
        decoder.finish()
        return b''.join(frame.encode() for frame in frames)

    streams = [b'', b''.join(frame.encode() for frame in frames), Frame(0xffff, bytes(65531)).encode()]
    for wire in streams:
        for chunk in (1, 2, 3, 4, 7, 257, 65535):
            compare('stream', struct.pack('>H', chunk) + wire,
                    lambda: decode(wire, chunk), 'stream_decodes')
    valid = encode_message(0x601, b'opaque', auxiliary=0xffffffff)
    malformed = [struct.pack('>HH', 1, length) for length in range(4)]
    malformed.extend(valid[:cut] for cut in range(1, len(valid)))
    malformed.append(Frame(1, b'').encode() + b'\x00')
    for wire in malformed:
        compare('stream', b'\x00\x01' + wire, lambda: decode(wire, 1), 'stream_decodes')

    def header(wire):
        decoder = FrameDecoder()
        frame, = decoder.feed(wire)
        decoder.finish()
        decoded = MessageHeader.from_frame(frame)
        return struct.pack('>HHHHI', decoded.message_id, decoded.length,
                           decoded.flags, decoded.reserved, decoded.auxiliary)

    for size in range(20):
        wire = Frame(rng.randrange(65536), rng.randbytes(size)).encode()
        compare('header', wire, lambda: header(wire), 'header_decodes')
    return {**counts, 'live_server_tested': False, 'original_binary_executed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner), indent=2))
