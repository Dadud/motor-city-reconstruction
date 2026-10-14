#include "mco/drivetrain_coupling.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
namespace mco {
namespace {
float stored(double v) {
    if (!std::isfinite(v) || std::abs(v) > std::numeric_limits<float>::max())
        throw std::invalid_argument("finite drivetrain coupling value required");
    return static_cast<float>(v);
}
}
float environment_correction(float field, bool override_mode, bool enabled, std::int32_t selector) {
    stored(field);
    double base = override_mode ? stored(278.15) : stored(288.15);
    const auto selected = enabled ? selector : 0;
    if (selected == 2) base -= 20;
    else if (selected == 1) base -= 10;
    const auto correction = stored(double(stored(1.25)) - (base*double(stored(.00087))+
                                double(stored(double(field)+500))*double(stored(.000002173))));
    return std::clamp(correction, stored(.95), stored(1.05));
}
DrivetrainCouplingOutput couple_drivetrain(const DrivetrainCoupling& s) {
    for (float v : {s.curve_torque,s.effective_torque,s.drag_factor,s.drag_speed,s.engagement,s.coupling_resistance})
        stored(v);
    const double correction = environment_correction(s.environment_field, s.environment_override,
                                s.environment_selector_enabled, s.environment_selector);
    const float power = std::max(stored(double(s.rpm)*double(s.curve_torque)*double(stored(.00010471976))), 0.f);
    const float drag = stored(double(s.drag_factor)*s.drag_speed);
    const double corrected = correction*double(s.effective_torque)-drag;
    double acceleration;
    if (s.gear_index == 1 || s.engagement == 0) acceleration = corrected;
    else if (s.engagement >= 1) acceleration = -double(s.coupling_resistance)+std::min(corrected,0.0);
    else acceleration = (1-double(s.engagement)*s.engagement)*corrected-s.coupling_resistance;
    return {power,drag,stored(corrected),stored(acceleration),static_cast<float>(correction)};
}
}
