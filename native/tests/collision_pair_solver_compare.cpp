#include "mco/collision_pair_geometry.hpp"
#include <iomanip>
#include <iostream>

int main() {
    std::cout << std::setprecision(9);
    mco::CollisionPairBody owner{};
    mco::CollisionPairBody target{};
    while (std::cin >> owner.box.center[0]) {
        for (std::size_t i = 1; i < 3; ++i) std::cin >> owner.box.center[i];
        for (auto& axis : owner.box.axes) for (auto& value : axis) std::cin >> value;
        for (auto& value : owner.box.half_extents) std::cin >> value;
        unsigned mode = 0;
        std::cin >> owner.mass >> mode >> owner.gate >> owner.peer_gate;
        owner.mode = static_cast<std::uint8_t>(mode);
        for (auto& value : target.box.center) std::cin >> value;
        for (auto& axis : target.box.axes) for (auto& value : axis) std::cin >> value;
        for (auto& value : target.box.half_extents) std::cin >> value;
        std::cin >> target.mass >> mode >> target.gate >> target.peer_gate;
        target.mode = static_cast<std::uint8_t>(mode);
        const auto result = mco::resolve_collision_pair(owner, target);
        std::cout << static_cast<int>(result.collided) << ' ' << result.correction_steps;
        for (float value : result.owner.box.center) std::cout << ' ' << value;
        for (float value : result.target.box.center) std::cout << ' ' << value;
        std::cout << '\n';
    }
}
