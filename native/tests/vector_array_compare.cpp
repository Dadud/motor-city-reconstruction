#include "mco/geometry_transform.hpp"
#include <iomanip>
#include <iostream>
#include <limits>
#include <vector>

int main() {
    std::cout << std::setprecision(std::numeric_limits<float>::max_digits10);
    std::size_t count = 0;
    while (std::cin >> count) {
        if (count > 4096) return 2;
        std::vector<float> input(count * 3), output(count * 3);
        std::array<float,3> translation{};
        for (auto& value : input) if (!(std::cin >> value)) return 2;
        for (auto& value : translation) if (!(std::cin >> value)) return 2;
        try {
            mco::add_vector_to_points(input.data(), translation, output.data(), count);
        } catch (...) { return 3; }
        for (std::size_t i = 0; i < output.size(); ++i)
            std::cout << (i == 0 ? "" : " ") << output[i];
        std::cout << '\n';
    }
}
