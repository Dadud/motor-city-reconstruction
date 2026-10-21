#pragma once
#include <array>
#include <cstdint>

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

struct OwnerBoxPointResult {
    bool inside;
    std::array<float, 3> target_local_point;
    std::array<float, 3> owner_world_point;
    std::array<float, 3> owner_direction;
};

struct PairContactNormalResult {
    std::array<float, 3> normal;
    unsigned selected_axis;
    bool near_center_branch;
};

struct CollisionPairBody {
    OrientedCollisionBox box;
    float mass;
    std::uint8_t mode;
    float gate;
    float peer_gate;
};

struct CollisionPairResult {
    bool collided;
    CollisionPairBody owner;
    CollisionPairBody target;
    unsigned correction_steps;
    bool has_contact;
    std::array<float, 3> last_contact;
    bool has_normal;
    std::array<float, 3> last_normal;
};

// Complete bounded translation of original helper 0x45b8e0.
OrientedBoxPointResult oriented_box_point_test(
    const OrientedCollisionBox& owner,
    const OrientedCollisionBox& target,
    const std::array<double, 3>& normalized_target_point);

// Complete bounded translations of original helpers 0x45bb70 and 0x45be10.
OwnerBoxPointResult owner_point_direction_test(
    const OrientedCollisionBox& owner,
    const OrientedCollisionBox& target,
    const std::array<double, 3>& normalized_owner_point);
OwnerBoxPointResult owner_point_contact_test(
    const OrientedCollisionBox& owner,
    const OrientedCollisionBox& target,
    const std::array<double, 3>& normalized_owner_point);

// Complete bounded translation of original helper 0x45bfe0.
PairContactNormalResult select_pair_contact_normal(
    const OrientedCollisionBox& owner,
    const OrientedCollisionBox& target,
    const std::array<double, 3>& projected_center,
    bool side);

// Bounded translation of the sampled pair resolver at original 0x45af30.
CollisionPairResult resolve_collision_pair(
    const CollisionPairBody& owner,
    const CollisionPairBody& target,
    unsigned max_corrections = 32);
} // namespace mco
