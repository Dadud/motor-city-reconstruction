"""Recovered spring/shock record fields and native validation ranges.

Force response and the shock coefficient's conversion to damping remain to trace.
"""
from dataclasses import dataclass
import math


def values(record):
    if len(record.values)<2 or record.mass is None:
        raise ValueError('suspension requires mass and two physics values')
    if not all(math.isfinite(v) for v in (record.mass,*record.values[:2])):
        raise ValueError('non-finite suspension values')
    return record.values[:2]


@dataclass(frozen=True)
class Spring:
    rate: float
    style: int
    mass: float

    def roll_contribution(self,track_width,front=True):
        """Native 0x54a840 axle contribution, applied once per axle.

        The original loader accumulates this on LF or LR attachment only.
        This is a response parameter, not a vertical wheel force.
        """
        if not math.isfinite(track_width) or track_width<=0:
            raise ValueError('positive finite axle width is required')
        arm=track_width*(0.76 if front else 0.68)
        return arm*self.rate*arm*0.0087265

    @classmethod
    def from_physics(cls,record):
        rate,style=values(record)
        style=round(style)
        if not 2<=record.mass<=30 or not 10000<=rate<=120000 or not 0<=style<=3:
            raise ValueError('spring outside native validation ranges')
        return cls(rate,style,record.mass)


@dataclass(frozen=True)
class Shock:
    coefficient: float
    length: float
    mass: float

    @classmethod
    def from_physics(cls,record):
        coefficient,length=values(record)
        if not 2<=record.mass<=10 or not 0.2<=coefficient<=0.4 or not 0.1016<=length<=0.4064:
            raise ValueError('shock outside native validation ranges')
        return cls(coefficient,length,record.mass)
