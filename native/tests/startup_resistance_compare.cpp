#include "mco/startup_resistance.hpp"
#include <bit>
#include <cstdint>
#include <iostream>

int main() {
    unsigned mode;
    std::uint32_t selector, a, b, c;
    while (std::cin >> mode >> selector >> a) {
        if (mode == 0) {
            std::cout << std::bit_cast<std::uint64_t>(mco::startup_surface_factor(
                selector, std::bit_cast<float>(a))) << '\n';
        } else if (mode == 1 && std::cin >> b >> c) {
            const auto output = mco::startup_resistance_table(std::bit_cast<float>(a),
                std::bit_cast<float>(b), std::bit_cast<float>(c), selector);
            for (unsigned i = 0; i < output.size(); ++i) {
                if (i) std::cout << ' ';
                std::cout << std::bit_cast<std::uint32_t>(output[i]);
            }
            std::cout << '\n';
        } else return 2;
    }
}
