#include "mco/load_transfer.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace mco {
namespace {
float stored(double value) {
    if (!std::isfinite(value) || std::abs(value) > std::numeric_limits<float>::max())
        throw std::invalid_argument("finite float32 load-transfer value required");
    return static_cast<float>(value);
}
}

std::array<float, 4> transfer_load(const LoadTransferInput& state) {
    std::array<float, 4> loads{};
    for (std::size_t i = 0; i < loads.size(); ++i) loads[i] = stored(state.loads[i]);
    const double attitude = stored(state.attitude);
    const double longitudinal = stored(state.longitudinal_acceleration);
    const double lateral = stored(state.lateral_acceleration);
    const double speed = stored(state.speed), mass = stored(state.mass);
    const double wheelbase = stored(state.wheelbase);
    const double ft = stored(state.front_track), rt = stored(state.rear_track);
    double height = stored(state.height_parameter);
    const double fo = stored(state.front_offset), ro = stored(state.rear_offset);
    if (*std::min_element(loads.begin(), loads.end()) < 0 || mass <= 0 ||
        wheelbase <= 0 || ft <= 0 || rt <= 0)
        throw std::invalid_argument("nonnegative loads and positive mass/dimensions required");
    height = stored(height * static_cast<double>(stored(0.9090909)));
    if (std::abs(attitude) > 0.25) return loads;
    const double threshold = stored(0.1962);
    if (std::abs(longitudinal) > threshold) {
        const double correction = stored(-longitudinal * (height / wheelbase) * mass * 0.5);
        for (std::size_t i = 0; i < loads.size(); ++i)
            loads[i] = std::max(0.0f, stored(static_cast<double>(loads[i]) +
                                           (i < 2 ? correction : -correction)));
    }
    if (std::abs(lateral) > threshold && std::abs(speed) > 6.0) {
        // Both axle sums use the longitudinally corrected, clamped loads.
        const double front = stored((static_cast<double>(loads[0]) + loads[1]) *
            static_cast<double>(stored(0.101936795)) *
            (((height - fo * static_cast<double>(stored(0.8))) * lateral) / ft));
        const double rear = stored((static_cast<double>(loads[2]) + loads[3]) *
            static_cast<double>(stored(0.101936795)) *
            (((height - ro * static_cast<double>(stored(0.8))) * lateral) / rt));
        loads[0] = std::max(0.0f, stored(static_cast<double>(loads[0]) + front));
        loads[1] = std::max(0.0f, stored(static_cast<double>(loads[1]) - front));
        loads[2] = std::max(0.0f, stored(static_cast<double>(loads[2]) + rear));
        loads[3] = std::max(0.0f, stored(static_cast<double>(loads[3]) - rear));
    }
    return loads;
}
} // namespace mco
