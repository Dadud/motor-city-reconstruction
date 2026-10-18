"""Native comparison driver for the scene_area cell.

The oracle builds the corpus and proves the native harness against original
execution; this driver only feeds stdin and compares. Scaffolded: connect the
corpus before trusting a green result.
"""
import argparse
import hashlib
import json
import subprocess


def verify(runner, lines, expected):
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',text=True,
        capture_output=True,check=True,timeout=120)
    observed=[tuple(map(int,line.split())) for line in result.stdout.splitlines()]
    if observed!=expected:
        for index,(got,want) in enumerate(zip(observed,expected)):
            if got!=want:
                raise AssertionError((index,got[:8],want[:8]))
        raise AssertionError((len(observed),len(expected)))
    return dict(cases=len(lines),maximum_absolute_error=0,
        scope='native comparison for scene_area')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner,[],[])))
