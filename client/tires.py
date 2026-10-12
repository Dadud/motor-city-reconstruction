"""Tire dimensions recovered from 0x53a1f0 and 0x5a39d0.

0x67d900 loads values; 0x6690a0 embeds them at 0x404; 0x52c2e0 copies
Val1/2/3 from 0x42c/0x430/0x434 to tire offsets 0x3c/0x40/0x44.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class TireDimensions:
    width_mm: float
    aspect_percent: float
    rim_inches: float

    @classmethod
    def from_physics(cls,record):
        """Interpret an explicitly selected tire PhysicsRecord."""
        if len(record.values)<3:
            raise ValueError('tire physics requires width, aspect and rim values')
        return cls(*record.values[:3])

    def __post_init__(self):
        if not all(math.isfinite(v) and v>0 for v in (self.width_mm,self.aspect_percent,self.rim_inches)):
            raise ValueError('positive finite tire dimensions are required')
        if self.width_mm>2000 or self.aspect_percent>200 or self.rim_inches>100:
            raise ValueError('tire dimensions exceed supported bounds')

    @property
    def sidewall(self):
        return self.width_mm*0.001*self.aspect_percent*0.01

    @property
    def radius(self):
        return self.rim_inches*0.0254*0.5+self.sidewall

    @property
    def stance_adjustment(self):
        """Native 0x53bf20: extra placement allowance for large tires."""
        return max(self.radius-0.37,0)
