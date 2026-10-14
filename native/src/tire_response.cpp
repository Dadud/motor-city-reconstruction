#include "mco/tire_response.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace mco {
namespace {
float stored(double value) {
    if (!std::isfinite(value) || std::abs(value) > std::numeric_limits<float>::max())
        throw std::invalid_argument("finite float32 wheel response value required");
    const float result = static_cast<float>(value);
    if (!std::isfinite(result))
        throw std::invalid_argument("wheel response overflowed float32");
    return result;
}
} // namespace

float wheel_response(const WheelResponseTable& table, double angle_coefficient,
                     const WheelCurveInput& wheel, bool secondary, bool alternate_load) {
    std::array<float, 26> knots{};
    for (std::size_t i = 0; i < knots.size(); ++i) knots[i] = stored(table[i]);
    const double coefficient = stored(angle_coefficient);
    const double slip = stored(wheel.slip_angle);
    const double angle = stored(wheel.secondary_angle);
    const double load = stored(wheel.normal_load);
    const double surface = stored(wheel.surface_multiplier);
    if (load < 0) throw std::invalid_argument("nonnegative normal load required");
    const double degrees = stored(slip * 180.0);
    const double coordinate = std::min(std::abs(degrees), 25.0);
    const auto index = static_cast<std::size_t>(std::floor(coordinate));
    const double first = knots[index];
    const double last = knots[std::min(index + 1, std::size_t{25})];
    const double curve = stored(first + (last - first) * (coordinate - index));
    const double scaled_load = stored(load * static_cast<double>(stored(0.00025)));
    double scale;
    if (secondary) {
        scale = scaled_load > 1.0
            ? stored(std::clamp(static_cast<double>(stored(scaled_load *
                     static_cast<double>(stored(2.83)) - 2.0)), 1.0, 5.0))
            : std::max(0.0, scaled_load);
    } else if (alternate_load) {
        const double bounded = std::clamp(scaled_load, 0.0, 3.5);
        const double polynomial = stored(bounded * bounded * static_cast<double>(stored(-0.1941)) +
                                         bounded * static_cast<double>(stored(1.2262)));
        scale = std::clamp(polynomial, 0.0, 2.0);
    } else if (scaled_load > 1.0) {
        const double polynomial = stored(scaled_load * scaled_load * static_cast<double>(stored(-0.1941)) +
                                         scaled_load * static_cast<double>(stored(1.2262)) -
                                         static_cast<double>(stored(0.031)));
        scale = std::clamp(polynomial, 1.0, 2.5);
    } else {
        scale = std::clamp(scaled_load, 0.0, 1.0);
    }
    double angle_term = angle * 180.0 * coefficient * load;
    if (secondary) angle_term *= static_cast<double>(stored(0.15));
    double response = (angle_term + scale * curve) * surface;
    if ((secondary && degrees < 0.0) || (!secondary && degrees > 0.0)) response = -response;
    return stored(response);
}
} // namespace mco
