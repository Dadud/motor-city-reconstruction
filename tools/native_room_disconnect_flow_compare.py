"""Asset-free native/Python disconnect action traces and complete observed images."""
import argparse
import random
import struct
import subprocess

from client.room_disconnect_flow import RoomDisconnectFlow


KINDS = {name: index for index, name in enumerate(('reset_container', 'yield_pending', 'enqueue',
                                                  'query_completion', 'pump_application', 'complete'))}


def image(rng, connected=1, pending=0):
    output = bytearray(rng.randbytes(0x3c0))
    struct.pack_into('<H', output, 0xec, connected)
    struct.pack_into('<I', output, 0x3a8, pending)
    return bytes(output)


def snapshot(flow):
    action = flow.action
    return (struct.pack('<9I', KINDS[action.kind], action.owner_offset is not None, action.owner_offset or 0,
                        action.tracked, action.operation_id is not None, action.operation_id or 0,
                        action.result is not None, (action.result or 0) & 0xffffffff,
                        action.argument is not None)
            + (action.argument or b'') + flow.room_image)


def cases():
    rng = random.Random(0x44d750)
    for pending in (0, 1, 0xffffffff):
        for wait in (False, True):
            source = image(rng, 0, pending)
            yield source, wait, [(0, source), (0, source)]
    for wait in (False, True):
        for becomes_connected in (0, 1):
            source = image(rng, 1, 5)
            commands = [(0, source), (0, source), (1, image(rng, 0, 3)),
                        (1, image(rng, becomes_connected, 0))]
            if becomes_connected:
                commands.append((2, 0xffffffff if wait else None))
                if wait:
                    commands += [(3, None), (4, 0), (3, -6)]
            yield source, wait, commands
    source = image(rng)
    yield source, False, [(0, source), (0, source), (2, None)]
    for operation_id in (1, 0x80000000, 0xffffffff):
        for result in (-0x80000000, -51, -6, 0, 1, 0x7fffffff):
            for misses in (0, 1, 3):
                source = image(rng)
                commands = [(0, source), (0, source), (2, operation_id)]
                commands += [(command, value) for _ in range(misses) for command, value in ((3, None), (4, 0))]
                commands.append((3, result))
                yield source, True, commands
    for abort in (-0x80000000, -1, 1, 0x7fffffff):
        source = image(rng)
        yield source, True, [(0, source), (0, source), (2, 7), (3, None), (4, abort)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', help='built mco_room_disconnect_flow_compare executable')
    args = parser.parse_args()
    matched = 0
    for index, (source, wait, commands) in enumerate(cases()):
        flow = RoomDisconnectFlow(source, wait_for_completion=wait)
        wire = bytearray(struct.pack('<III', len(source), wait, len(commands)) + source)
        expected = bytearray(snapshot(flow))
        for command, value in commands:
            if command in (0, 1):
                wire.extend(struct.pack('<III', command, 0, 0) + value)
                (flow.container_reset if command == 0 else flow.pending_yielded)(value)
            else:
                wire.extend(struct.pack('<III', command, value is not None, (value or 0) & 0xffffffff))
                {2: flow.enqueued, 3: flow.completion_queried, 4: flow.application_pumped}[command](value)
            expected.extend(snapshot(flow))
        actual = subprocess.run([args.executable], input=bytes(wire), capture_output=True, check=True, timeout=10)
        if actual.stdout != expected:
            raise RuntimeError(f'native disconnect action/image trace differs at case {index}')
        matched += 1
    print(f'{matched} native/Python disconnect traces match byte-for-byte at every action; '
          'actual waits, pumps, queues and network effects remain external.')


if __name__ == '__main__':
    main()
