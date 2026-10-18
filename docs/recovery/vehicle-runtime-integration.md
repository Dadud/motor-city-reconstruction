# Persistent vehicle and engine integration

`RecoveredVehicleRuntime` is an authored integration adapter around the recovered vehicle update, engine pipeline and linear update. It retains state across ticks and preserves the flags, motion and longitudinal-speed aliases already established in the Python model. Unresolved vehicle and engine children and the linear-enable predicate require explicit callbacks.

A 120-frame native/Python composition check passes on MSVC and Zig with maximum absolute error 0.0 using synthetic stage responses. CI runs this comparison on Windows and Linux; Linux execution remains pending the CI run. Release builds execute explicit contract checks for missing callbacks, host rollback and tick count.

The adapter commits host state atomically on success; that rollback contract is authored and stronger than original partial mutation. Synthetic forces and callback responses do not establish original driving behavior or playable gameplay.
