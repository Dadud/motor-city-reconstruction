# Renderer plane-height equation

`0x4b71a0` solves for the Y coordinate on a plane from its XYZ normal, a
reference point on the plane, and an input XZ point. It evaluates
`reference.y - ((point.x-reference.x)*normal.x + (point.z-reference.z)*normal.z) / normal.y`.

`client/render_plane_math.py::plane_height` rounds inputs and the returned
height to binary32. Five hundred twelve direct calls against the installed
`mcity.exe` match the returned float word exactly across varied nonvertical
planes. A zero Y component does not define a finite height and is outside the
supported domain.
