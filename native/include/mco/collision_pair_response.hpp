#pragma once

#include "mco/collision_impulse.hpp"
#include <array>
#include <cstdint>

namespace mco {
struct CollisionImpactBody {
    std::uint32_t address{};
    std::array<float, 3> position{};
    std::array<float, 3> linear_velocity{};
    std::array<float, 3> angular_turn_velocity{};
    std::array<float, 3> center_of_mass_local{};
    CollisionInertia inertia{};
    float mass{};
    std::uint8_t mode{};
    float response_coefficient{};
    float gate{};
    float peer_gate{};
    std::array<std::uint8_t, 0x400> contact_record{};
};

struct CollisionImpactResult {
    bool collided{};
    CollisionImpactBody owner;
    CollisionImpactBody target;
    unsigned samples{};
    int impact_status{};
    float effective_mass{};
};

// Supplied-state translation of the sampled impact response at 0x458530.
CollisionImpactResult resolve_pair_impulse(
    const CollisionImpactBody& owner,
    const CollisionImpactBody& target,
    const std::array<float, 3>& contact_point,
    const std::array<float, 3>& normal,
    float threshold_coefficient,
    float sliding_coefficient);
} // namespace mco
