"""The game's shared six-word additive random generator (REA 0x6f0fa0).

The state is explicit here so callers can reproduce a generated sequence
without mutating process globals. Words use the original little-endian order.
"""
from dataclasses import dataclass

_MASK = 0xffffffff


@dataclass
class RandomState:
    words: tuple[int, int, int, int, int, int]

    def __post_init__(self):
        if len(self.words) != 6 or any(type(word) is not int or not 0 <= word <= _MASK
                                       for word in self.words):
            raise ValueError('random state must contain six unsigned 32-bit words')

    def next_u32(self) -> int:
        """Advance the native carry recurrence and return its new word zero."""
        s0, s1, s2, s3, s4, s5 = self.words
        u1 = (s4 + s5) & _MASK
        carry1 = int(u1 < s5 and u1 < s4)
        u2 = (u1 + carry1 + s3) & _MASK
        u3 = (u2 + int(u2 < s3) + s2) & _MASK
        u4 = (u3 + int(u3 < s2) + s1) & _MASK
        d0 = (s0 + u4 + int(u4 < s1)) & _MASK
        s5_next = (s5 + 1) & _MASK
        self.words = (d0, u4, u3, u2, u1, s5_next)

        # The original handles the all-words-wrapped case by propagating one
        # additional carry from the least-significant word to every higher word.
        if (s5_next == 0 and u1 == 0 and u2 == 0 and u3 == 0 and u4 == 0):
            self.words = ((d0 + 1) & _MASK, 1, 1, 1, 1, 0)
        return self.words[0]
