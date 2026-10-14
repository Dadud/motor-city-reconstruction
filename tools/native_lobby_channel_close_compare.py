"""Asset-free native/Python local channel-close arguments and plain frame parity."""
import argparse
import itertools
import struct
import subprocess

from client.lobby_channel_close import ChannelCloseRequest, native_close_arguments


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', help='built mco_lobby_channel_close_compare executable')
    args = parser.parse_args()
    values = (0,1,7,44,0x12345678,0x7fffffff,0x80000000,0x87654321,0xffffffff)
    matched = 0
    for selector, channel in itertools.product(values, repeat=2):
        request = ChannelCloseRequest(channel)
        expected = native_close_arguments(selector, channel) + request.payload() + request.frame().encode()
        actual = subprocess.run([args.executable], input=struct.pack('<QQ', selector, channel),
                                capture_output=True, check=True, timeout=10)
        if actual.stdout != expected:
            raise RuntimeError(f'native channel-close encoding differs at case {matched}')
        matched += 1
    for selector, channel in ((0x100000000,1),(1,0x100000000),(0xffffffffffffffff,1),(1,0xffffffffffffffff)):
        rejected = subprocess.run([args.executable], input=struct.pack('<QQ', selector, channel),
                                  capture_output=True, timeout=10)
        if rejected.returncode == 0 or rejected.stdout:
            raise RuntimeError('wide native channel-close input was narrowed without rejection')
    print(f'{matched} native/Python local arguments, payloads and plain frames match; four wide inputs rejected. '
          'Interface zero policy and live sends remain separate checks.')


if __name__ == '__main__':
    main()
