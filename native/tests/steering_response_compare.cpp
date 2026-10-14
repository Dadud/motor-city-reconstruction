#include "mco/steering_response.hpp"
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
int main() {
    std::cout << std::setprecision(std::numeric_limits<float>::max_digits10);
    std::size_t count = 0;
    while (true) {
        std::int64_t raw; double speed;
        if (!(std::cin >> raw)) return std::cin.eof() ? 0 : 2;
        if (++count > 100000 || !(std::cin >> speed) || raw < std::numeric_limits<std::int32_t>::min() ||
            raw > std::numeric_limits<std::int32_t>::max()) return 2;
        try { std::cout << mco::steering_response(static_cast<std::int32_t>(raw), speed) << '\n'; }
        catch (const std::invalid_argument&) { return 3; }
    }
}
