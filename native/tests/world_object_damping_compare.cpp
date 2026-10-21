#include "mco/world_object_damping.hpp"
#include <iomanip>
#include <iostream>

int main() {
    std::cout << std::setprecision(9);
    mco::WorldObjectMotion state{};
    while (std::cin >> state.contact_counter) {
        for (auto& value : state.linear_velocity) if (!(std::cin >> value)) return 2;
        for (auto& value : state.angular_velocity) if (!(std::cin >> value)) return 2;
        const auto result = mco::update_world_object_motion(state);
        for (const auto value : result.linear_velocity) std::cout << value << ' ';
        for (const auto value : result.angular_velocity) std::cout << value << ' ';
        std::cout << '\n';
    }
}
