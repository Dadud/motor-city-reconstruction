#include "mco/drivetrain_coupling.hpp"
#include <iomanip>
#include <iostream>
#include <limits>
int main() {
    std::cout << std::setprecision(std::numeric_limits<float>::max_digits10);
    std::size_t count=0;
    while (true) {
        mco::DrivetrainCoupling s{}; int override_mode, enabled;
        if (!(std::cin >> s.rpm)) return std::cin.eof() ? 0 : 2;
        if (++count>100000 || !(std::cin >> s.curve_torque >> s.effective_torque >> s.drag_factor
            >> s.drag_speed >> s.gear_index >> s.engagement >> s.coupling_resistance >> s.environment_field
            >> override_mode >> enabled >> s.environment_selector) || override_mode<0 || override_mode>1 || enabled<0 || enabled>1) return 2;
        s.environment_override=override_mode!=0; s.environment_selector_enabled=enabled!=0;
        try {
            const auto out=mco::couple_drivetrain(s);
            std::cout << out.power << ' ' << out.drag << ' ' << out.corrected_torque << ' '
                      << out.acceleration_input << ' ' << out.environment_correction << '\n';
        } catch (...) { return 3; }
    }
}
