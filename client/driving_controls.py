"""Original smoothed controls bound to recovered wheel-force consumers."""
from dataclasses import replace
from client.control_update import ControlState, update_controls


class DrivingControls:
    """Wrap the remaining child executor; retain the control record across ticks.

    execute(ControlCall, mutable_controls) must implement remote/gear effects and
    service queries. publish(controls, controller, force_inputs) synchronizes
    engine/brake state absent from the force-controller view. It is required;
    omitting engine flag writes would leave the shared owner inconsistent.
    """
    stages = frozenset(('control_update',))

    def __init__(self, controls, execute, external, publish):
        if not isinstance(controls, ControlState) or not all(map(callable, (execute, external, publish))):
            raise ValueError('explicit controls, child behavior, remaining stages and publication required')
        self.controls, self.execute = controls, execute
        self.external, self.publish = external, publish
        self.calls = ()

    def __call__(self, call, s, force):
        if call.stage != 'control_update':
            return self.external(call, s, force)
        # +0x474 bit 0x200 controls both remote input and controller branches.
        self.controls.remote_controls = bool(s.flags & 0x200)
        out = update_controls(self.controls, self.execute)
        self.controls, self.calls = out.state, out.calls
        force.tire = replace(force.tire, raw_control=out.state.steering)
        force.spin = replace(force.spin, direction_mode=out.state.output_gear)
        force.service_control = out.state.brake_output
        force.other_control = out.state.throttle_output
        # The field is named reverse_control by the input consumer and parking
        # control by force consumers. Preserve the actual +0xa6b byte alias.
        force.parking_control = bool(out.state.reverse_control)
        self.publish(self.controls, s, force)
