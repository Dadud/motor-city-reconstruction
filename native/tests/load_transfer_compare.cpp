#include "mco/load_transfer.hpp"

#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>

int main() {
    std::cout << std::setprecision(std::numeric_limits<float>::max_digits10);
    std::size_t count = 0;
    while (true) {
        mco::LoadTransferInput state{};
        if (!(std::cin >> state.loads[0])) return std::cin.eof() ? 0 : 2;
        if (++count > 100000 || !(std::cin >> state.loads[1] >> state.loads[2] >> state.loads[3] >>
              state.attitude >> state.longitudinal_acceleration >> state.lateral_acceleration >>
              state.speed >> state.mass >> state.wheelbase >> state.front_track >> state.rear_track >>
              state.height_parameter >> state.front_offset >> state.rear_offset)) return 2;
        try {
            const auto result = mco::transfer_load(state);
            std::cout << result[0] << ' ' << result[1] << ' ' << result[2] << ' ' << result[3] << '\n';
        } catch (const std::invalid_argument&) { return 3; }
    }
}
