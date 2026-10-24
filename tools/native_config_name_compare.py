"""Compare the default MCO name comparator across Python and C++."""
import json
import subprocess

from client.string_compare import compare_config_names
from tools.verify_config_name_compare import _names


def run(binary, cases=512):
    lines, expected = [], []
    for left, right in _names(cases):
        if len(left) > 512 or len(right) > 512:
            raise ValueError('comparison corpus exceeds fixed native image')
        image = bytearray(1024)
        image[:len(left)] = left
        image[512:512 + len(right)] = right
        lines.append('0 ' + ' '.join(map(str, (len(left), len(right), *image))))
        result = compare_config_names(left, right)
        expected.append(result & 0xffffffff)
    process = subprocess.run([str(binary)], input='\n'.join(lines) + '\n', text=True,
                             capture_output=True, check=True)
    actual = [int(line) for line in process.stdout.splitlines()]
    if actual != expected:
        index = next(i for i, values in enumerate(zip(actual, expected)) if values[0] != values[1])
        raise AssertionError({'case': index, 'native': actual[index], 'python': expected[index]})
    return {'cases': cases, 'result': 'exact', 'scope': 'default byte-fold mode'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(run(args.binary, args.cases)))
