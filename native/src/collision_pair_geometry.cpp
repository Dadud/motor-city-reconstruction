#include "mco/collision_pair_geometry.hpp"
#include <cmath>
#include <limits>
#include <stdexcept>

namespace mco {
namespace {
float stored(double value) {
    if (!std::isfinite(value) || std::abs(value) > std::numeric_limits<float>::max())
        throw std::invalid_argument("finite float32 collision value required");
    return static_cast<float>(value);
}
void validate(const OrientedCollisionBox& box) {
    for (float value : box.center)
        if (!std::isfinite(value)) throw std::invalid_argument("finite collision center required");
    for (float value : box.half_extents)
        if (!std::isfinite(value) || value < 0)
            throw std::invalid_argument("nonnegative finite collision extents required");
    for (const auto& axis : box.axes)
        for (float value : axis)
            if (!std::isfinite(value)) throw std::invalid_argument("finite collision axes required");
}
} // namespace

OrientedBoxPointResult oriented_box_point_test(
    const OrientedCollisionBox& owner,
    const OrientedCollisionBox& target,
    const std::array<double, 3>& normalized_target_point) {
    validate(owner);
    validate(target);
    std::array<float, 3> point{};
    for (std::size_t i = 0; i < 3; ++i) {
        if (!std::isfinite(normalized_target_point[i]))
            throw std::invalid_argument("finite normalized collision point required");
        point[i] = stored(normalized_target_point[i]);
    }

    std::array<float, 3> offset{};
    for (std::size_t i = 0; i < 3; ++i)
        offset[i] = stored(static_cast<double>(target.center[i]) - owner.center[i]);

    OrientedBoxPointResult result{};
    for (std::size_t i = 0; i < 3; ++i) {
        double center_projection = 0;
        for (std::size_t k = 0; k < 3; ++k)
            center_projection += static_cast<double>(owner.axes[i][k]) * offset[k];
        double extent_projection = 0;
        for (std::size_t j = 0; j < 3; ++j) {
            double axis_dot = 0;
            for (std::size_t k = 0; k < 3; ++k)
                axis_dot += static_cast<double>(owner.axes[i][k]) * target.axes[j][k];
            const float projected_axis = stored(axis_dot);
            const float scaled_axis = stored(
                static_cast<double>(projected_axis) * target.half_extents[j]);
            extent_projection += static_cast<double>(scaled_axis) * point[j];
        }
        result.owner_local_point[i] = stored(center_projection + extent_projection);
    }

    result.inside = true;
    for (std::size_t i = 0; i < 3; ++i)
        result.inside = result.inside &&
            -owner.half_extents[i] <= result.owner_local_point[i] &&
            result.owner_local_point[i] <= owner.half_extents[i];
    if (!result.inside) return result;

    for (std::size_t k = 0; k < 3; ++k) {
        double displacement = 0;
        double direction = 0;
        for (std::size_t j = 0; j < 3; ++j) {
            displacement += static_cast<double>(target.axes[j][k]) *
                            target.half_extents[j] * point[j];
            direction += static_cast<double>(target.axes[j][k]) * point[j];
        }
        result.target_world_point[k] = stored(target.center[k] + displacement);
        result.target_direction[k] = stored(direction);
    }
    const double squared = stored(
        static_cast<double>(result.target_direction[0]) * result.target_direction[0] +
        static_cast<double>(result.target_direction[1]) * result.target_direction[1] +
        static_cast<double>(result.target_direction[2]) * result.target_direction[2]);
    if (squared != 0) {
        const float inverse = stored(1.0 / std::sqrt(squared));
        for (auto& value : result.target_direction)
            value = stored(static_cast<double>(value) * inverse);
    }
    return result;
}
} // namespace mco
