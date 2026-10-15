#include "mco/rolling_resistance.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace mco {
namespace {
float stored(double value) {
    if (!std::isfinite(value) || std::abs(value) > std::numeric_limits<float>::max())
        throw std::invalid_argument("finite float32 resistance value required");
    return static_cast<float>(value);
}
}

ResistanceResult rolling_resistance(std::array<ResistanceWheel, 4> wheels,
    double speed, double front_coefficient, double rear_coefficient,
    double front_adjustment, double rear_adjustment, double body_angle,
    bool disabled_flag, bool mode_predicate, bool alternate) {
    speed = stored(speed);
    const double front = stored(front_coefficient), rear = stored(rear_coefficient);
    const double fa = stored(front_adjustment), ra = stored(rear_adjustment);
    const double angle = stored(body_angle);
    for (auto& wheel : wheels) {
        wheel.slip_angle = stored(wheel.slip_angle);
        wheel.normal_load = stored(wheel.normal_load);
        wheel.rolling_speed = stored(wheel.rolling_speed);
        wheel.speed_scale = stored(wheel.speed_scale);
        wheel.longitudinal_force = stored(wheel.longitudinal_force);
        if (wheel.normal_load < 0 || wheel.speed_scale <= 0)
            throw std::invalid_argument("nonnegative load and positive speed scale required");
    }
    if (std::abs(speed) < 2 || disabled_flag || mode_predicate) return {wheels, 0.0f};
    const double cosine = std::cos(std::abs(angle) * static_cast<double>(stored(6.2831855)));
    float last = 0;
    for (std::size_t i = 0; i < wheels.size(); ++i) {
        auto& wheel = wheels[i];
        double coefficient;
        if (wheel.surface_id == 2)
            coefficient = std::abs(speed) * static_cast<double>(stored(0.000096)) +
                                 static_cast<double>(stored(0.012));
        else if (wheel.surface_id == 3 || wheel.surface_id == 5)
            coefficient = std::abs(speed) * static_cast<double>(stored(0.000072)) +
                                 static_cast<double>(stored(0.013));
        else
            coefficient = std::abs(speed) * static_cast<double>(stored(0.000048)) +
                                 static_cast<double>(stored(0.01));
        const double axle = ((i < 2 ? fa : ra) + 1.0) * (i < 2 ? front : rear);
        // The x87 routine stores the combined product, not either input.
        const double scaled_resistance = stored(axle * (coefficient * 0.5));
        const double degrees = stored(std::abs(wheel.slip_angle * 180.0));
        const double amplification = std::clamp(static_cast<double>(stored(
            (degrees * static_cast<double>(stored(0.0831)) +
             degrees * degrees * static_cast<double>(stored(0.0988))) * 0.5 + 1.0)), 1.0, 8.0);
        const double projection = cosine * (alternate ? amplification : 1.0);
        last = stored(-(projection * wheel.normal_load *
                        scaled_resistance));
        if (wheel.rolling_speed < 0) last = -last;
        if (wheel.contact && 1.0 / wheel.speed_scale < std::abs(wheel.rolling_speed) &&
            wheel.normal_load != 0)
            wheel.longitudinal_force = stored(wheel.longitudinal_force + last);
    }
    return {wheels, last};
}
} // namespace mco
