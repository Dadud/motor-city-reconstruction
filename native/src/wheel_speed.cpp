#include "mco/wheel_speed.hpp"
#include <cmath>
#include <limits>
#include <stdexcept>
namespace mco {
namespace {
float stored(double value) {
    if (!std::isfinite(value) || std::abs(value) > std::numeric_limits<float>::max())
        throw std::invalid_argument("finite float32 wheel-speed value required");
    return static_cast<float>(value);
}
}
std::array<float, 4> project_wheel_speeds(const WheelSpeedState& state) {
    const double lateral = stored(state.lateral_velocity), longitudinal = stored(state.longitudinal_velocity);
    double yaw = stored(state.yaw_rate_turns);
    const double front = stored(state.front_offset), rear = stored(state.rear_offset);
    const double ft = stored(state.front_track), rt = stored(state.rear_track);
    if (ft <= 0 || rt <= 0) throw std::invalid_argument("positive axle tracks required");
    auto wheels = state.wheels;
    for (auto& w : wheels) {
        w.angle = stored(w.angle); w.spin_value = stored(w.spin_value); w.spin_scale = stored(w.spin_scale);
    }
    const double turn = stored(6.2831855);
    yaw = stored(yaw * turn);
    const double front_delta = stored(yaw * 0.5 * ft), rear_delta = stored(yaw * 0.5 * rt);
    std::array<float, 4> output{};
    for (std::size_t i = 0; i < 4; ++i) {
        const auto& w = wheels[i];
        const double local_lateral = i < 2 ? stored(lateral + yaw * front) : stored(lateral - yaw * rear);
        const double delta = i < 2 ? front_delta : rear_delta;
        const double local_longitudinal = stored(longitudinal + ((i == 0 || i == 3) ? delta : -delta));
        if (!w.contact) { output[i] = stored(w.spin_scale * w.spin_value); continue; }
        const double half_angle = stored(w.angle * 0.5), radians = half_angle * turn;
        const double sine_part = stored(std::sin(radians) * local_lateral);
        output[i] = stored(std::cos(radians) * local_longitudinal + sine_part);
    }
    return output;
}
}
