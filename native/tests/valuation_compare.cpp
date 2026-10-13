#include "mco/owned_valuation.hpp"
#include <iostream>
#include <iomanip>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

int main() {
#ifdef _WIN32
    _setmode(_fileno(stdin), _O_BINARY);
#endif
    mco::OwnedPartSlot slot{};
    while (std::cin.read(reinterpret_cast<char*>(slot.data()), slot.size())) {
        try {
            auto result = mco::calculate_owned_valuation(slot, {0.1, 0.75});
            if (!result) std::cout << "empty\n";
            else std::cout << result->repair_cost << ' ' << result->scrap_value << ' '
                           << std::hexfloat << result->wear_condition << '\n';
        } catch (const std::exception& error) {
            std::cerr << error.what() << '\n';
            return 1;
        }
    }
    return std::cin.gcount() == 0 ? 0 : 2;
}
