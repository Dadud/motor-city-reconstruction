"""Recovered startup resistance table, not the complete road-load model.

Addresses 0x53e620 and 0x550ed0 in the verified main executable. The caller
supplies finalized mass, area, coefficient and surface selector. Speed units and
the physical interpretation of the area coefficient still need caller recovery.
"""
from client.tire_response import f32


def startup_surface_factor(selector: int, speed: float) -> float:
    """Return the original unstored double intermediate (0x53e620)."""
    if type(selector) is not int or not 0 <= selector <= 0xffffffff:
        raise ValueError('uint32 surface selector required')
    speed = f32(speed)
    if speed < 1.:
        return 0.
    if selector == 2:
        return speed * f32(.000096) + f32(.012)
    if selector in (3, 5):
        return speed * f32(.000072) + f32(.013)
    return speed * f32(.000048) + f32(.01)


def startup_resistance_table(mass: float, coefficient: float, area: float,
                             selector: int) -> tuple[float, ...]:
    """Produce all 135 float32 entries written by original 0x550ed0."""
    mass, coefficient, area = map(f32, (mass, coefficient, area))
    # Original stores the mass-force product before entering the loop.
    mass_force = f32(mass * f32(9.81))
    output = []
    for index in range(135):
        rolling = startup_surface_factor(selector, float(index)) * f32(1.1) * mass_force
        aerodynamic = index * index * coefficient * area * f32(.5905)
        output.append(f32(aerodynamic + rolling))
    return tuple(output)
