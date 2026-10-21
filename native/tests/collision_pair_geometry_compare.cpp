#include "mco/collision_pair_geometry.hpp"
#include <iomanip>
#include <iostream>
#include <limits>

int main() {
    std::cout << std::setprecision(std::numeric_limits<float>::max_digits10);
    std::size_t count = 0;
    while (true) {
        mco::OrientedCollisionBox owner{}, target{};
        std::array<double, 3> point{};
        if (!(std::cin >> owner.center[0])) return std::cin.eof() ? 0 : 2;
        if (++count > 100000) return 2;
        for (std::size_t i = 1; i < 3; ++i) if (!(std::cin >> owner.center[i])) return 2;
        for (auto& axis : owner.axes) for (auto& value : axis) if (!(std::cin >> value)) return 2;
        for (auto& value : owner.half_extents) if (!(std::cin >> value)) return 2;
        for (auto& value : target.center) if (!(std::cin >> value)) return 2;
        for (auto& axis : target.axes) for (auto& value : axis) if (!(std::cin >> value)) return 2;
        for (auto& value : target.half_extents) if (!(std::cin >> value)) return 2;
        for (auto& value : point) if (!(std::cin >> value)) return 2;
        try {
            const auto result = mco::oriented_box_point_test(owner, target, point);
            std::cout << static_cast<int>(result.inside);
            for (float value : result.owner_local_point) std::cout << ' ' << value;
            for (float value : result.target_world_point) std::cout << ' ' << value;
            for (float value : result.target_direction) std::cout << ' ' << value;
            std::cout << '\n';
        } catch (...) { return 3; }
    }
}
