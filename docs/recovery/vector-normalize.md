# Shared vector normalization

The installed `mcity.exe` routine at `0x6f1100` computes a three-component
Euclidean magnitude through `0x6f1210`, forms its reciprocal, and stores each
input component multiplied by that reciprocal. The translation is
`client.matrix_math.normalize_vector3`; `normalized_cross3` reuses it after its
float-stored cross product.

`python -m tools.verify_normalize_vector3 "C:\Program Files (x86)\EA Games\Motor City Online\mcity.exe"`
compares all three binary32 outputs against direct bounded CPU emulation of the
original routine. The fixed-seed 517-call set includes ordinary vectors, a zero
vector, and small and large magnitudes; all finite words match exactly, and the
zero-vector NaNs match by classification. This verifies only this helper's
input/output contract, not its callers or full renderer integration.
