# Track color blend

`client/track_colors.py` translates the native `mcity.exe` routine at
`0x4956e0`. With the bypass global set, it returns the input ARGB word
unchanged. Otherwise, it reads the base color and divisor from native globals,
blends each RGB channel using `1/divisor` and its complement, halves the
weighted sum, rounds through binary32 and the x87 integer conversion, clamps
the channel to `[0, 255]`, and forces alpha to `0xff`.

The translation was compared against 1,024 calls to the exact shipped
executable, with randomized colors and divisors from 1 through 16, plus both
bypass and blend paths. Every returned 32-bit word matched. This validates the
routine for finite positive divisors in that range and bypass inputs; other
global states are not claimed.

REA function dossier: `ev_c8a393dd970cc0fa74bcc56b29f6fd0efdc0d3d0fc0e19307a1c2f38622bc4a4`.
The neighboring clamp routine at `0x6f1380` has its own reviewed translation.
