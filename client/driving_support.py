"""Original support predictor bound to the shared vehicle controller state."""
from dataclasses import replace
from client.support_prediction import predict_support


class DrivingSupport:
    """Compose with DrivingForces as its external child executor.

    Position, terrain context, local support points and query records live in
    prediction because the force controller does not own them. The external
    executor must update those values from recovered motion/preparation stages.
    The original terrain projection service is a mandatory separate boundary.
    """
    def __init__(self, prediction, project, external):
        if not callable(project) or not callable(external):
            raise ValueError('terrain projection and remaining stages required')
        if len(prediction.wheels) != 4:
            raise ValueError('four support records required')
        self.prediction, self.project, self.external = prediction, project, external

    def __call__(self, call, s, force_inputs):
        if call.stage != 'predict_support':
            return self.external(call, s, force_inputs)
        output = predict_support(replace(self.prediction, velocity=s.linear_velocity,
            to_world=s.to_world, fallback_surface=s.fallback_surface,
            wheels=tuple(replace(old, clear_reference=w.clear_reference)
                for old, w in zip(self.prediction.wheels, s.wheels))), self.project)
        self.prediction = output.state
        s.support_count = output.state.support_count
        for w, support in zip(s.wheels, output.state.wheels):
            w.contact = support.contact
            w.clear_threshold = support.support_delta
            w.surface_record = support.record.surface_code
            w.surface_class = support.surface_class
