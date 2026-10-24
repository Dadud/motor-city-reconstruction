#include "mco/normal_load.hpp"
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
int main() {
    std::cout << std::setprecision(std::numeric_limits<float>::max_digits10);
    std::size_t count = 0;
    while (true) {
        unsigned mask;
        if (!(std::cin >> mask)) return std::cin.eof() ? 0 : 2;
        if (++count > 100000 || mask > 15) return 2;
        mco::NormalLoadInput s{};
        for (std::size_t i = 0; i < 4; ++i) s.support[i] = (mask & (1u << i)) != 0;
        if (!(std::cin >> s.pitch >> s.bank >> s.mass >> s.wheelbase >> s.front_track >>
              s.rear_track >> s.height_parameter >> s.front_lever >> s.rear_lever >> s.speed >>
              s.curvature_scale >> s.vertical_correction)) return 2;
        for (auto& scale : s.wheel_scales) if (!(std::cin >> scale)) return 2;
        try {
            const auto forces = mco::normal_force_vectors(s);
            for (const auto& force : forces)
                std::cout << force[0] << ' ' << force[1] << ' ' << force[2] << ' ';
            std::cout << '\n';
        } catch (const std::invalid_argument&) { return 3; }
    }
}
