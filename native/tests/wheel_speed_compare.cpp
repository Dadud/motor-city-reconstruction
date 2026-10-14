#include "mco/wheel_speed.hpp"
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
int main() {
    std::cout << std::setprecision(std::numeric_limits<float>::max_digits10);
    std::size_t count = 0;
    while (true) {
        mco::WheelSpeedState s{};
        if (!(std::cin >> s.lateral_velocity)) return std::cin.eof() ? 0 : 2;
        if (++count > 100000 || !(std::cin >> s.longitudinal_velocity >> s.yaw_rate_turns >>
            s.front_offset >> s.rear_offset >> s.front_track >> s.rear_track)) return 2;
        for (auto& w : s.wheels) {
            int contact;
            if (!(std::cin >> w.angle >> contact >> w.spin_value >> w.spin_scale) || contact < 0 || contact > 1) return 2;
            w.contact = contact != 0;
        }
        try {
            const auto r = mco::project_wheel_speeds(s);
            std::cout << r[0] << ' ' << r[1] << ' ' << r[2] << ' ' << r[3] << '\n';
        } catch (const std::invalid_argument&) { return 3; }
    }
}
