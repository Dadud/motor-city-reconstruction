#include "mco/suspension_load_correction.hpp"
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
int main() {
    std::cout << std::setprecision(std::numeric_limits<float>::max_digits10);
    std::size_t count = 0;
    while (true) {
        mco::SuspensionLoadInput s{};
        if (!(std::cin >> s.loads[0])) return std::cin.eof() ? 0 : 2;
        unsigned mask; int enabled, disable; std::int64_t mode;
        if (++count > 100000 || !(std::cin >> s.loads[1] >> s.loads[2] >> s.loads[3] >> mask >>
            s.attitude >> enabled >> s.speed >> s.bank_angle >> s.pitch_angle >> s.mass >> s.mass_offset >>
            s.front_weight_parameter >> s.rear_weight_parameter >> s.front_lever >> s.rear_lever >>
            s.wheelbase >> s.rear_track >> s.gear_factor >> s.torque >> mode >> disable)) return 2;
        if (mask > 15 || enabled < 0 || enabled > 1 || disable < 0 || disable > 1 ||
            mode < std::numeric_limits<std::int32_t>::min() || mode > std::numeric_limits<std::int32_t>::max()) return 2;
        for (std::size_t i = 0; i < 4; ++i) s.support[i] = (mask & (1u << i)) != 0;
        s.enabled = enabled != 0; s.disable_torque = disable != 0; s.component_mode = static_cast<std::int32_t>(mode);
        try {
            const auto r = mco::correct_suspension_load(s);
            std::cout << r[0] << ' ' << r[1] << ' ' << r[2] << ' ' << r[3] << '\n';
        } catch (const std::invalid_argument&) { return 3; }
    }
}
