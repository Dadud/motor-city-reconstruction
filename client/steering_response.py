"""Original speed-dependent steering input shaping, 0x541930.

Raw control and speed producers, maximum steering and wheel geometry are external.
"""
from client.tire_response import f32


def steering_response(raw_control: int, speed: float):
    if type(raw_control) is not int or not -0x80000000 <= raw_control <= 0x7fffffff:
        raise ValueError('signed int32 steering observation required')
    speed = f32(speed)
    magnitude = f32(abs(f32(raw_control)) * f32(0.007874016))
    blend = max(0.0, min(1.0, f32(abs(speed) * f32(0.022369863))))
    # Keep the original expanded subtraction, including its rounding context.
    shaped = f32((1.0 - blend) * magnitude +
                 (1.0 - (1.0 - blend)) * magnitude * magnitude)
    result = min(1.0, shaped)
    return -result if raw_control < 0 else result
