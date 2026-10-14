#include "mco/wheel_speed.hpp"
#include <limits>
#include <stdexcept>
namespace {
void check(bool condition, const char* message) { if (!condition) throw std::runtime_error(message); }
}
int main() {
    mco::WheelSpeedState s{};
    s.longitudinal_velocity = 20; s.front_track = 1.6; s.rear_track = 1.7;
    s.front_offset = 1.2; s.rear_offset = 1.5;
    for (auto& w : s.wheels) w = {0, true, -3.75, 0.25};
    check(mco::project_wheel_speeds(s) == std::array<float, 4>{20, 20, 20, 20}, "straight speed failed");
    s.yaw_rate_turns = 0.3;
    const auto yaw = mco::project_wheel_speeds(s);
    check(yaw[0] > 20 && yaw[1] < 20 && yaw[2] < 20 && yaw[3] > 20, "native slot yaw signs failed");
    for (unsigned mask = 0; mask < 16; ++mask) {
        auto t = s;
        for (std::size_t i = 0; i < 4; ++i) t.wheels[i].contact = (mask & (1u << i)) != 0;
        const auto r = mco::project_wheel_speeds(t);
        for (std::size_t i = 0; i < 4; ++i)
            check(r[i] == (t.wheels[i].contact ? yaw[i] : -0.9375f), "contact/spin selection failed");
    }
    s.wheels[2].contact = false; s.wheels[2].angle = std::numeric_limits<double>::infinity();
    bool rejected = false;
    try { mco::project_wheel_speeds(s); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "airborne nonfinite angle accepted");
}
