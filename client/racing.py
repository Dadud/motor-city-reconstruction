"""Authored offline time trial using ordered gates from decoded road slices."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Gate:
    position: tuple
    forward: tuple
    right: tuple
    left: float
    right_limit: float

    def crossing_fraction(self, previous, current):
        before = sum((previous[i]-self.position[i])*self.forward[i] for i in range(3))
        after = sum((current[i]-self.position[i])*self.forward[i] for i in range(3))
        if not before <= 0 < after:
            return None
        fraction = -before/(after-before)
        point = tuple(previous[i]+fraction*(current[i]-previous[i]) for i in range(3))
        lateral = sum((point[i]-self.position[i])*self.right[i] for i in range(3))
        if not -self.left <= lateral <= self.right_limit:
            return None
        # Exclude crossing the gate on a different level of an overlapping track.
        if abs(point[1]-self.position[1]) > 4:
            return None
        return fraction


class TimeTrial:
    def __init__(self, track):
        slices = track.slices
        if len(slices) < 3:
            raise ValueError('time trial needs at least three road slices')
        separation = math.dist(slices[0].position, slices[-1].position)
        end_spacing = math.dist(slices[-2].position, slices[-1].position)
        self.closed = separation <= max(10, end_spacing*1.5)
        stride = max(1, len(slices)//24)
        indices = list(range(0, len(slices)-1, stride))
        if not self.closed:
            indices.append(len(slices)-1)
        self.gates = tuple(Gate(slices[i].position, slices[i].forward, slices[i].right,
                                slices[i].left_limit, slices[i].right_limit) for i in indices)
        self.reset()

    def reset(self):
        self.next_gate = 1
        self.elapsed = 0
        self.started = self.finished = False
        self.completed = []

    @property
    def best(self):
        return min(self.completed) if self.completed else None

    def update(self, previous, current, dt):
        if not math.isfinite(dt) or dt <= 0:
            raise ValueError('invalid time-trial interval')
        if self.finished:
            return None
        if not self.started:
            if math.dist(previous, current) <= 1e-9:
                return None
            self.started = True
        fraction = self.gates[self.next_gate].crossing_fraction(previous, current)
        old_elapsed = self.elapsed
        self.elapsed += dt
        if fraction is None:
            return None
        final = self.next_gate == (0 if self.closed else len(self.gates)-1)
        if final:
            result = old_elapsed+fraction*dt
            self.completed.append(result)
            if self.closed:
                self.next_gate = 1
                self.elapsed = (1-fraction)*dt
            else:
                self.elapsed = result
                self.finished = True
            return result
        self.next_gate = (self.next_gate+1) % len(self.gates)
        return None

    def label(self):
        minutes, seconds = divmod(self.elapsed, 60)
        best = f' · Best {self.best:.2f}s' if self.best is not None else ''
        if self.finished:
            return f'Finished {self.elapsed:.2f}s · R to race again'
        passed = len(self.gates)-1 if self.next_gate == 0 else self.next_gate-1
        return f'{"Lap " + str(len(self.completed)+1) if self.closed else "Sprint"} · {int(minutes):02}:{seconds:05.2f} · Gates {passed}/{len(self.gates)-1}{best}'
