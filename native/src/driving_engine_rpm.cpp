#include "mco/driving_engine_rpm.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
namespace mco {
namespace {
float stored(double v) {
    if (!std::isfinite(v) || std::abs(v) > std::numeric_limits<float>::max())
        throw std::invalid_argument("finite driving RPM value required");
    return static_cast<float>(v);
}
std::int32_t nearest(float v) {
    // Explicit ties-to-even; independent of the host rounding mode.
    const double low = std::floor(static_cast<double>(v));
    const double fraction = static_cast<double>(v) - low;
    const double result = low + (fraction > .5 || (fraction == .5 && std::fmod(low, 2) != 0));
    if (result <= std::numeric_limits<std::int32_t>::min() || result >= std::numeric_limits<std::int32_t>::max())
        throw std::invalid_argument("RPM conversion exceeds supported range");
    return static_cast<std::int32_t>(result);
}
}
DrivingEngineRPM update_driving_engine_rpm(DrivingEngineRPM s, std::int32_t minimum) {
    for (const double v : {double(s.throttle), double(s.normalized_rpm), double(s.inertia_factor),
         double(s.acceleration_input), double(s.angular_speed), double(s.gear_speed_factor), double(s.longitudinal_speed)})
        stored(v);
    if (s.normalized_rpm < -10 || s.normalized_rpm > 10)
        throw std::invalid_argument("normalized RPM outside comparison range");
    const double rads = stored(.10471976), scale = stored(9.549296);
    const auto target_raw = std::int64_t(s.idle_rpm) + nearest(stored(double(s.throttle)*double(stored(1.1))*
                                      (double(s.configured_max_rpm)-s.idle_rpm)));
    const double configured = std::min(std::max(double(target_raw), double(s.idle_rpm)), double(s.configured_max_rpm));
    const auto target_sum = std::int64_t(s.target_rpm) + nearest(stored((configured-s.target_rpm)*std::exp(-double(s.normalized_rpm))*.0625));
    if (target_sum <= std::numeric_limits<std::int32_t>::min() || target_sum >= std::numeric_limits<std::int32_t>::max())
        throw std::invalid_argument("target RPM exceeds supported range");
    s.target_rpm = static_cast<std::int32_t>(target_sum);
    const double raw = s.enabled ? stored(double(s.inertia_factor)*s.acceleration_input) : 0;
    s.acceleration_output = stored((1-double(s.normalized_rpm))*raw);
    if (raw < 0) {
        s.acceleration_output = std::max(s.acceleration_output, stored(double(s.normalized_rpm)*double(stored(-200))));
        const double delta = std::min(stored(double(s.acceleration_output)*.03125),
                stored(-(double(s.rpm)-s.target_rpm)*rads*double(s.inertia_factor)*.03125));
        s.angular_speed = stored(double(s.angular_speed)+delta);
    } else if (s.rpm < s.target_rpm) {
        const auto candidate = nearest(stored(((1-double(s.normalized_rpm))*raw*.03125+s.angular_speed)*scale));
        s.angular_speed = stored(double(std::min(candidate, s.target_rpm))*rads);
    } else {
        if (s.gear_index != 1) {
            const auto driven = nearest(stored(double(s.gear_speed_factor)*s.longitudinal_speed));
            s.target_rpm = std::max(static_cast<std::int32_t>(std::abs(driven)), s.target_rpm);
        }
        s.angular_speed = stored(double(s.angular_speed)-(double(s.rpm)-s.target_rpm)*rads*.03125);
    }
    if (s.enabled) {
        s.rpm = std::max(std::min(nearest(stored(double(s.angular_speed)*scale)), s.limiter_rpm), minimum);
        s.angular_speed = stored(double(s.rpm)*rads);
    } else {
        s.rpm = 0; s.angular_speed = 0;
    }
    return s;
}
}
