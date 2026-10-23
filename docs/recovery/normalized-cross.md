# Normalized cross-product helper

`client/matrix_math.py::normalized_cross3` translates shared native function
`0x6f10d0`. It forms the three cross-product components, stores them as
binary32, computes the original Euclidean magnitude, and scales each component
by the reciprocal magnitude with binary32 output stores. A zero cross product
produces three NaNs, matching the original x87 divide-by-zero and multiply
behavior.

The helper matched every output bit in 512 deterministic direct calls against
the shipped x86 executable, and the zero-vector case also produced NaNs in both
implementations. The direct comparison uses finite vector inputs and does not
cover cross-product overflow. This is a shared dependency of track generation,
including `0x495240`.

REA function dossier: `ev_7b1bd95013f2546fef3945bf78d72699c9c474ee0f52cf3a4f7c4f003206a4d4`.
