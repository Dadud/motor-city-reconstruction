#pragma once
#include <array>

namespace mco {
struct OrientedCollisionBox {
    std::array<float, 3> center;
    // The three basis rows stored at original owner offsets +0x78/+0x84/+0x90.
    std::array<std::array<float, 3>, 3> axes;
    std::array<float, 3> half_extents;
};

struct OrientedBoxPointResult {
    bool inside;
    std::array<float, 3> owner_local_point;
    std::array<float, 3> target_world_point;
    std::array<float, 3> target_direction;
};

// Complete bounded translation of original helper 0x45b8e0.
OrientedBoxPointResult oriented_box_point_test(
    const OrientedCollisionBox& owner,
    const OrientedCollisionBox& target,
    const std::array<double, 3>& normalized_target_point);
} // namespace mco
