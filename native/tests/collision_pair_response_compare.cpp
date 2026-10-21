#include "mco/collision_pair_response.hpp"
#include <cstring>
#include <iomanip>
#include <iostream>
#include <limits>

namespace {
bool read_body(mco::CollisionImpactBody& body) {
    unsigned mode = 0;
    if (!(std::cin >> body.address)) return false;
    for (auto& v : body.position) if (!(std::cin >> v)) return false;
    for (auto& v : body.linear_velocity) if (!(std::cin >> v)) return false;
    for (auto& v : body.angular_turn_velocity) if (!(std::cin >> v)) return false;
    for (auto& v : body.center_of_mass_local) if (!(std::cin >> v)) return false;
    if (!(std::cin >> body.inertia.inverse_mass)) return false;
    for (auto& v : body.inertia.inverse_inertia) if (!(std::cin >> v)) return false;
    for (auto& v : body.inertia.world_to_body) if (!(std::cin >> v)) return false;
    for (auto& v : body.inertia.body_to_world) if (!(std::cin >> v)) return false;
    if (!(std::cin >> body.mass >> mode >> body.response_coefficient >> body.gate >> body.peer_gate)) return false;
    body.mode = static_cast<std::uint8_t>(mode);
    return true;
}
void print_record(const mco::CollisionImpactBody& body) {
    const auto& b = body.contact_record;
    auto u32 = [&](std::size_t offset) {
        return static_cast<std::uint32_t>(b[offset]) |
               (static_cast<std::uint32_t>(b[offset + 1]) << 8) |
               (static_cast<std::uint32_t>(b[offset + 2]) << 16) |
               (static_cast<std::uint32_t>(b[offset + 3]) << 24);
    };
    auto f32 = [&](std::size_t offset) {
        float value{};
        const std::uint32_t bits = u32(offset);
        std::memcpy(&value, &bits, sizeof(value));
        return value;
    };
    std::cout << ' ' << u32(0x3c4) << ' ' << f32(0x3c8);
    for (std::size_t i = 0; i < 3; ++i) std::cout << ' ' << f32(0x3cc + i * 4);
    for (std::size_t i = 0; i < 3; ++i) std::cout << ' ' << f32(0x3d8 + i * 4);
    std::cout << ' ' << u32(0x3e4);
    for (std::size_t i = 0; i < 3; ++i) std::cout << ' ' << f32(0x3e8 + i * 4);
    std::cout << ' ' << u32(0x3f4) << ' ' << u32(0x3f8) << ' ' << f32(0x3fc);
}
} // namespace

int main() {
    std::cout << std::setprecision(std::numeric_limits<float>::max_digits10);
    while (true) {
        mco::CollisionImpactBody owner{}, target{};
        if (!read_body(owner)) return std::cin.eof() ? 0 : 2;
        if (!read_body(target)) return 2;
        std::array<float, 3> contact{}, normal{};
        float threshold = 0.f, sliding = 0.f;
        for (auto& v : contact) if (!(std::cin >> v)) return 2;
        for (auto& v : normal) if (!(std::cin >> v)) return 2;
        if (!(std::cin >> threshold >> sliding)) return 2;
        try {
            const auto result = mco::resolve_pair_impulse(owner, target, contact,
                                                           normal, threshold, sliding);
            std::cout << static_cast<int>(result.collided) << ' ' << result.samples
                      << ' ' << result.impact_status << ' ' << result.effective_mass;
            for (float v : result.owner.linear_velocity) std::cout << ' ' << v;
            for (float v : result.owner.angular_turn_velocity) std::cout << ' ' << v;
            for (float v : result.target.linear_velocity) std::cout << ' ' << v;
            for (float v : result.target.angular_turn_velocity) std::cout << ' ' << v;
            print_record(result.owner);
            print_record(result.target);
            std::cout << '\n';
        } catch (...) { return 3; }
    }
}
