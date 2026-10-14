#include "mco/driving_engine_rpm.hpp"
#include <iomanip>
#include <iostream>
#include <limits>
int main() {
    std::cout << std::setprecision(std::numeric_limits<float>::max_digits10);
    std::size_t count = 0;
    while (true) {
        mco::DrivingEngineRPM s{};
        int enabled; std::int32_t minimum;
        if (!(std::cin >> s.idle_rpm)) return std::cin.eof() ? 0 : 2;
        if (++count > 100000 || !(std::cin >> s.configured_max_rpm >> s.throttle >> s.normalized_rpm
            >> s.target_rpm >> enabled >> s.inertia_factor >> s.acceleration_input >> s.angular_speed
            >> s.rpm >> s.limiter_rpm >> s.gear_index >> s.gear_speed_factor >> s.longitudinal_speed
            >> s.acceleration_output >> minimum) || enabled < 0 || enabled > 1) return 2;
        s.enabled = enabled != 0;
        try {
            const auto out = mco::update_driving_engine_rpm(s, minimum);
            std::cout << out.target_rpm << ' ' << out.rpm << ' ' << out.angular_speed << ' '
                      << out.acceleration_output << '\n';
        } catch (...) { return 3; }
    }
}
