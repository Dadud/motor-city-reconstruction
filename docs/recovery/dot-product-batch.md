# Batch vector dot product

Routine `0x6f1160` walks `count` consecutive three-float vectors, computes a
dot product of each with one supplied direction vector, and stores one
binary32 result per vector. A zero count performs no stores.

`dot_product_batch` composes the existing scalar `dot_3_f32` translation.
`tools.verify_dot_product_batch.py` compares 512 randomized direct original
calls bit-for-bit, including counts from zero through sixteen, and checks a
guard word after the output span on every call. The routine's inputs and output
buffer are explicit; higher-level camera scheduling is outside its scope.

Static provenance: retained Ghidra 12.1.4 pseudocode and native body from the
REA export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
