#include "mco/rolling_resistance.hpp"

#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>

int main() {
    std::cout << std::setprecision(std::numeric_limits<float>::max_digits10);
    std::size_t count = 0;
    while (true) {
        double speed, front, rear, fa, ra, angle;
        int disabled, mode, alternate;
        if (!(std::cin >> speed)) return std::cin.eof() ? 0 : 2;
        if (++count > 100000 || !(std::cin >> front >> rear >> fa >> ra >> angle >>
                                  disabled >> mode >> alternate)) return 2;
        if (disabled < 0 || disabled > 1 || mode < 0 || mode > 1 ||
            alternate < 0 || alternate > 1) return 2;
        std::array<mco::ResistanceWheel, 4> wheels{};
        for (auto& wheel : wheels) {
            std::uint64_t surface;
            int contact;
            if (!(std::cin >> wheel.slip_angle >> surface >> wheel.normal_load >>
                  wheel.rolling_speed >> wheel.speed_scale >> contact >> wheel.longitudinal_force) ||
                surface > std::numeric_limits<std::uint32_t>::max() || contact < 0 || contact > 1)
                return 2;
            wheel.surface_id = static_cast<std::uint32_t>(surface);
            wheel.contact = contact != 0;
        }
        try {
            const auto result = mco::rolling_resistance(wheels, speed, front, rear, fa, ra,
                                                       angle, disabled != 0, mode != 0, alternate != 0);
            std::cout << result.last_contribution;
            for (const auto& wheel : result.wheels)
                std::cout << ' ' << wheel.slip_angle << ' ' << wheel.surface_id << ' '
                          << wheel.normal_load << ' ' << wheel.rolling_speed << ' '
                          << wheel.speed_scale << ' ' << wheel.contact << ' ' << wheel.longitudinal_force;
            std::cout << '\n';
        } catch (const std::invalid_argument&) { return 3; }
    }
}
