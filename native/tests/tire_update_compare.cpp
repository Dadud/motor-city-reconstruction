#include "mco/tire_update.hpp"
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
namespace {
bool curve(mco::TireCurves& c) {
    for (auto& value : c.primary) if (!(std::cin >> value)) return false;
    for (auto& value : c.secondary) if (!(std::cin >> value)) return false;
    return static_cast<bool>(std::cin >> c.angle_coefficient);
}
}
int main() {
    std::cout << std::setprecision(std::numeric_limits<float>::max_digits10);
    std::size_t count = 0;
    while (true) {
        std::int64_t raw; unsigned modes; int rear,alternate;
        mco::TireUpdateState s{};
        if (!(std::cin >> raw)) return std::cin.eof() ? 0 : 2;
        if (++count > 100000 || raw < std::numeric_limits<std::int32_t>::min() ||
            raw > std::numeric_limits<std::int32_t>::max()) return 2;
        s.raw_control = static_cast<std::int32_t>(raw);
        if (!(std::cin >> s.speed >> s.mass_parameter >> s.front_lever >> s.rear_lever >> s.front_track >>
              s.wheelbase >> s.maximum_steering >> s.longitudinal_velocity >> s.lateral_velocity >>
              s.lateral_acceleration >> s.yaw_rate >> s.body_slip >> rear >> modes >> alternate) ||
              rear < 0 || rear > 1 || alternate < 0 || alternate > 1 || modes > 15) return 2;
        s.rear_steering = rear != 0; s.alternate_load = alternate != 0;
        for (std::size_t i = 0; i < 4; ++i) s.mode_observations[i] = (modes & (1u << i)) != 0;
        if (!curve(s.front_curves) || !curve(s.rear_curves)) return 2;
        for (auto& w : s.wheels) {
            int contact;
            if (!(std::cin >> w.steering_angle >> w.slip_angle >> w.secondary_angle >> w.projected_speed >>
                  w.normal_load >> contact >> w.surface_multiplier >> w.lateral_force >>
                  w.longitudinal_force >> w.secondary_response) || contact < 0 || contact > 1) return 2;
            w.contact = contact != 0;
        }
        try {
            const auto r = mco::update_tires(s);
            std::cout << r.lateral_velocity << ' ' << r.lateral_acceleration << ' ' << r.yaw_rate;
            for (const auto& w : r.wheels)
                std::cout << ' ' << w.steering_angle << ' ' << w.slip_angle << ' ' << w.secondary_angle <<
                    ' ' << w.projected_speed << ' ' << w.normal_load << ' ' << w.contact <<
                    ' ' << w.surface_multiplier << ' ' << w.lateral_force << ' ' << w.longitudinal_force <<
                    ' ' << w.secondary_response;
            std::cout << '\n';
        } catch (const std::invalid_argument&) { return 3; }
    }
}
