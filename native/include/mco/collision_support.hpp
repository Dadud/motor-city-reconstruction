#pragma once

#include "mco/collision_pair_response.hpp"
#include "mco/track_surface_world.hpp"
#include <array>
#include <cstddef>
#include <cstdint>

namespace mco {
// Supplied-world translation of the original 22-point support caller 0x459150.
struct SupportQuery {
    std::uint32_t index{};
    std::array<float,3> relative_point{};
    std::array<std::byte,68> record{};
    std::array<float,3> normal{};
    float signed_distance{};
    bool has_surface{};
    bool eligible{};
};

struct SupportGeometryResult {
    std::array<float,3> position{};
    std::array<float,66> relative_points{};
    std::array<SupportQuery,22> queries{};
    std::array<float,3> correction{};
};

struct SupportImpactResult {
    CollisionImpactBody body{};
    std::array<std::uint32_t,22> impacted_points{};
    std::uint32_t support_count{};
};

SupportGeometryResult correct_support_geometry(
    const TrackSurfaceWorld& world,
    const std::array<float,3>& position,
    const std::array<float,9>& orientation,
    const std::array<float,66>& local_points,
    const std::array<std::byte,68>& query_seed,
    float vertical_velocity);

SupportImpactResult resolve_support_contacts(
    const TrackSurfaceWorld& world,
    const CollisionImpactBody& body,
    const SupportGeometryResult& geometry,
    const std::array<std::array<float,2>,32>& coefficient_table,
    float response_scale,
    std::uint32_t response_mode);
} // namespace mco
