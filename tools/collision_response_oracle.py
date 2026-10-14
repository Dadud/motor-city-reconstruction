"""CPU-only comparison of complete original collision helper 0x458390."""
import argparse
import itertools
import json
import struct
from client.collision_response import tangential_response
from tools.native_oracle import DynoOracle


class CollisionResponseOracle(DynoOracle):
    def response(self, vector, normal, threshold, sliding):
        self._reset()
        a, b, out = self.inputs, self.inputs+32, self.inputs+64
        before = struct.pack('<3f', *vector)+bytes(20)
        before += struct.pack('<3f', *normal)+bytes(20)
        self.cpu.mem_write(a, before+bytes([0xa5])*12)
        stack = self.frame-0x1000
        self.cpu.mem_write(stack, struct.pack('<IIIffI', self.stop, a, b,
                                             threshold, sliding, out))
        self._run(0x458390, self.stop, count=1000)
        if bytes(self.cpu.mem_read(a, 64)) != before:
            raise AssertionError('original helper changed inputs')
        return (self.cpu.reg_read(self.reg.UC_X86_REG_EAX),
                struct.unpack('<3f', self.cpu.mem_read(out, 12)))


def cases():
    vectors = ((0,0,0), (0,-1,0), (1,-1,0), (4,-2,3),
               (-4,2,-3), (0,1,0), (1e-5,-1e-5,2e-5),
               (1000,-2000,500), (2,-0.125,4))
    normals = ((0,1,0), (0,-1,0), (1,0,0), (0,0,1),
               (0.6,0.8,0), (-0.3,0.4,0.8660254), (0,0,0), (0,2,0))
    for v, n, t, s in itertools.product(vectors, normals,
                                         (0,0.25,0.75,1,2,4),
                                         (0,0.1,0.5,1)):
        yield v,n,t,s
    # Include strict inequality equality and its adjacent float32 values.
    for t in (1.9999998807907104,2,2.000000238418579):
        yield (0,-1,0),(0,1,0),t,0.5


def compare(executable):
    oracle = CollisionResponseOracle(executable)
    count, statuses, max_error = 0, set(), 0.0
    for v,n,t,s in cases():
        status, vector = oracle.response(v,n,t,s)
        actual = tangential_response(v,n,t,s)
        if status != actual.status:
            raise AssertionError((v,n,t,s,status,actual))
        for a,b in zip(vector,actual.vector):
            error = abs(a-b)
            max_error = max(max_error,error)
            if error > max(1e-6, abs(a)*3e-7):
                raise AssertionError((v,n,t,s,vector,actual))
        count += 1
        statuses.add(status)
    return {'cases':count,'statuses':sorted(statuses),'max_error':max_error,
            'entry':'0x458390','complete_helper':True,
            'collision_detection_included':False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    args = parser.parse_args()
    print(json.dumps(compare(args.executable)))
