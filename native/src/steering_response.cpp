#include "mco/steering_response.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
namespace mco {
namespace {
float stored(double value) {
    if (!std::isfinite(value) || std::abs(value) > std::numeric_limits<float>::max())
        throw std::invalid_argument("finite float32 steering value required");
    return static_cast<float>(value);
}
}
float steering_response(std::int32_t raw_control, double speed) {
    speed = stored(speed);
    // Convert before absolute value so INT32_MIN never incurs integer overflow.
    const double magnitude = stored(std::abs(static_cast<double>(stored(raw_control))) *
                                    static_cast<double>(stored(0.007874016)));
    const double blend = std::clamp(static_cast<double>(stored(std::abs(speed) *
                                  static_cast<double>(stored(0.022369863)))), 0.0, 1.0);
    const double shaped = stored((1.0 - blend) * magnitude +
                                 (1.0 - (1.0 - blend)) * magnitude * magnitude);
    const float result = static_cast<float>(std::min(1.0, shaped));
    return raw_control < 0 ? -result : result;
}
}
