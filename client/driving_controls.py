"""Original smoothed controls bound to recovered wheel-force consumers."""
from dataclasses import replace
from client.control_update import ControlState, update_controls


class DrivingControls:
    """Wrap the remaining child executor; retain the control record across ticks.

    execute(ControlCall, mutable_controls) must implement remote/gear effects and
    service queries. publish(controls, controller, force_inputs) synchronizes
    engine/brake state absent from the force-controller view. It is required;
    omitting engine flag writes would leave the shared owner inconsistent.
    remote_mode(controller, inputs) supplies the original vehicle identity and
    policy predicate; its local-vehicle identity differs from control-rate mode.
    """
    stages = frozenset(('control_update',))

    def __init__(self, controls, execute, external, publish, remote_mode):
        if not isinstance(controls, ControlState) or not all(map(callable, (execute, external, publish, remote_mode))):
            raise ValueError('explicit controls, child behavior, remaining stages and publication required')
        self.controls, self.execute = controls, execute
        self.external, self.publish = external, publish
        self.remote_mode = remote_mode
        self.calls = ()

    def __call__(self, call, s, force):
        if call.stage != 'control_update':
            return self.external(call, s, force)
        # Original 0x43b570 also tests flags 2/0x10 and a local-vehicle setting.
        # Its identity/policy context is distinct from control-rate local_player.
        mode=self.remote_mode(s,force)
        if type(mode) not in (int,bool) or not 0<=mode<=0xffffffff:
            raise ValueError('explicit uint32 remote-control mode required')
        self.controls.remote_controls = bool(mode)
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
