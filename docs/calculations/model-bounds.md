# Translated and mirrored part bounds

`client/model_bounds.py` and `native/src/model_bounds.cpp` translate complete original `0x4c3e50`: take a selected
FCE part's vertices, optionally negate local X, add its part origin, and return
the translated minimum/maximum coordinates. Empty parts return no bounds.
Inputs and translated coordinates use original float32 storage. On equal values,
the original selects the latest candidate, including the sign of zero; Python's
ordinary `min`/`max` tie handling does not reproduce this.

Source: external `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
REA evidence `ev_8174c1d226cc78f73e1bff103eefd5154c30c2feb96f494b909f0c63b431c976`.
The authored input boundary rejects nonfinite data and more than one million
vertices; valid original images remain external.

Verification: 860 complete original-function executions, both mirror modes,
status and all 24 output bytes exact. The corpus includes 414 actual body parts
from stock model archives and authored empty, translated and signed-zero cases.
Empty-output sentinels remain unchanged in the original execution.
Thirty-two authored C++/Python cases also match status and all signed output bits.

```sh
python -m tools.model_bounds_oracle /path/to/mcity.exe --game "/path/to/Motor City Online"
python -m tools.native_model_bounds_compare /path/to/mco_model_bounds_compare
```

This primitive does not establish assembled collision dimensions. Original
`0x52be40` first places/scales wheels and attachments, selects parts, unions
their transformed bounds, then recenters model part origins and dummy markers.
Its dependent selection/placement and complete model startup remain unresolved.
The C++ primitive builds in `mco_core`; it does not supply those caller stages.
