"""Compare every native/Python start action and full synthetic owner image."""
import argparse
import itertools
import struct
import subprocess

from client.game_start_flow import GameStartFlow


def snapshot(flow):
    action = flow.action
    kinds = {'enqueue_task_5': 0, 'query_completion': 1, 'pump_application': 2,
             'query_room_status': 3, 'complete': 4}
    fields = [kinds[action.kind], action.owner_offset, action.operation_id, action.channel_id, action.result,
              action.argument.hex() if action.argument is not None else None, flow.network_image.hex()]
    return ' '.join('-' if value is None else str(value) for value in fields) + '\n'


def compare(executable):
    count = 0
    scripts = [('e 9', 'q 1 -2147483648'), ('e 9', 'q 0 0', 'p 1 456'),
               ('e 9', 'q 1 0', 'p -1 456')]
    for result, status, delayed in itertools.product((0, 1, 0x7fffffff), (None, 4, 8), (False, True)):
        script = ['e 4294967295']
        if delayed:
            script += ['q 0 0', 'p 0 456']
        script += [f'q 1 {result}', 'p 0 789', 's 1 255', 'p 0 4294967295',
                   f's {int(status is not None)} {status or 0}']
        scripts.append(tuple(script))
    for selector, channel in ((0, 0), (7, 123), (0xffffffff, 0xffffffff)):
        for script in scripts:
            image = bytearray(b'\xa5' * 0x600)
            struct.pack_into('<I', image, 0x5cc, selector)
            struct.pack_into('<I', image, 0x160, channel)
            flow = GameStartFlow(bytes(image))
            expected = snapshot(flow)
            for line in script:
                words = line.split()
                if words[0] == 'e': flow.enqueued(int(words[1]))
                elif words[0] == 'q': flow.completion_queried(int(words[2]) if int(words[1]) else None)
                elif words[0] == 's': flow.room_status_queried(int(words[2]) if int(words[1]) else None)
                else:
                    observed = bytearray(flow.network_image)
                    struct.pack_into('<I', observed, 0x160, int(words[2]))
                    flow.application_pumped(int(words[1]), observed_network_image=bytes(observed))
                expected += snapshot(flow)
            actual = subprocess.run([executable], input=f'{selector} {channel}\n' + '\n'.join(script) + '\n',
                                    capture_output=True, text=True, check=True, timeout=10)
            if actual.stdout != expected:
                raise AssertionError(f'native game-start trace differs in case {count}')
            count += 1
    return count


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(f'{compare(parser.parse_args().executable)} native/Python game-start traces match every action and full image.')
