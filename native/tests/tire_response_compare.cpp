#include "mco/tire_response.hpp"

#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>

int main() {
    std::cout << std::setprecision(std::numeric_limits<float>::max_digits10);
    std::size_t count = 0;
    while (true) {
        int secondary, alternate;
        if (!(std::cin >> secondary)) return std::cin.eof() ? 0 : 2;
        if (++count > 100000 || !(std::cin >> alternate) || secondary < 0 || secondary > 1 ||
            alternate < 0 || alternate > 1) return 2;
        double coefficient;
        mco::WheelCurveInput wheel{};
        mco::WheelResponseTable table{};
        if (!(std::cin >> coefficient >> wheel.slip_angle >> wheel.secondary_angle >>
              wheel.normal_load >> wheel.surface_multiplier)) return 2;
        for (auto& knot : table) if (!(std::cin >> knot)) return 2;
        try {
            std::cout << mco::wheel_response(table, coefficient, wheel, secondary != 0,
                                             alternate != 0) << '\n';
        } catch (const std::invalid_argument&) {
            return 3;
        }
    }
}
