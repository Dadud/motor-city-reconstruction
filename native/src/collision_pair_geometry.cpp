#include "mco/collision_pair_geometry.hpp"
#include <algorithm>
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
OwnerBoxPointResult owner_point_test(
    const OrientedCollisionBox& owner,
    const OrientedCollisionBox& target,
    const std::array<double, 3>& normalized_point,
    bool with_direction) {
    validate(owner);
    validate(target);
    std::array<float, 3> point{};
    for (std::size_t i = 0; i < 3; ++i) {
        if (!std::isfinite(normalized_point[i]))
            throw std::invalid_argument("finite normalized collision point required");
        point[i] = stored(normalized_point[i]);
    }
    std::array<float, 3> offset{};
    for (std::size_t i = 0; i < 3; ++i)
        offset[i] = stored(static_cast<double>(target.center[i]) - owner.center[i]);

    OwnerBoxPointResult result{};
    for (std::size_t i = 0; i < 3; ++i) {
        double center_projection = 0;
        for (std::size_t k = 0; k < 3; ++k)
            center_projection += static_cast<double>(target.axes[i][k]) * offset[k];
        double extent_projection = 0;
        for (std::size_t j = 0; j < 3; ++j) {
            double axis_dot = 0;
            for (std::size_t k = 0; k < 3; ++k)
                axis_dot += static_cast<double>(owner.axes[j][k]) * target.axes[i][k];
            const float scaled_axis = stored(static_cast<double>(stored(axis_dot)) *
                                              owner.half_extents[j]);
            extent_projection += static_cast<double>(scaled_axis) * point[j];
        }
        result.target_local_point[i] = stored(extent_projection - center_projection);
    }
    result.inside = true;
    for (std::size_t i = 0; i < 3; ++i)
        result.inside = result.inside &&
            -target.half_extents[i] <= result.target_local_point[i] &&
            result.target_local_point[i] <= target.half_extents[i];
    if (!result.inside) return result;

    for (std::size_t k = 0; k < 3; ++k) {
        double displacement = 0;
        double direction = 0;
        for (std::size_t j = 0; j < 3; ++j) {
            displacement += static_cast<double>(owner.axes[j][k]) *
                            owner.half_extents[j] * point[j];
            direction -= static_cast<double>(owner.axes[j][k]) * point[j];
        }
        result.owner_world_point[k] = stored(owner.center[k] + displacement);
        if (with_direction) result.owner_direction[k] = stored(direction);
    }
    if (with_direction) {
        const double squared = stored(
            static_cast<double>(result.owner_direction[0]) * result.owner_direction[0] +
            static_cast<double>(result.owner_direction[1]) * result.owner_direction[1] +
            static_cast<double>(result.owner_direction[2]) * result.owner_direction[2]);
        if (squared != 0) {
            const float inverse = stored(1.0 / std::sqrt(squared));
            for (auto& value : result.owner_direction)
                value = stored(static_cast<double>(value) * inverse);
        }
    }
    return result;
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

OwnerBoxPointResult owner_point_direction_test(
    const OrientedCollisionBox& owner, const OrientedCollisionBox& target,
    const std::array<double, 3>& point) {
    return owner_point_test(owner, target, point, true);
}

OwnerBoxPointResult owner_point_contact_test(
    const OrientedCollisionBox& owner, const OrientedCollisionBox& target,
    const std::array<double, 3>& point) {
    return owner_point_test(owner, target, point, false);
}

PairContactNormalResult select_pair_contact_normal(
    const OrientedCollisionBox& owner, const OrientedCollisionBox& target,
    const std::array<double, 3>& projected_center, bool side) {
    validate(owner);
    validate(target);
    std::array<float, 3> projection{};
    for (std::size_t i = 0; i < 3; ++i) {
        if (!std::isfinite(projected_center[i]))
            throw std::invalid_argument("finite projected collision center required");
        projection[i] = stored(projected_center[i]);
    }
    const auto& basis = side ? target : owner;
    const auto& other = side ? owner : target;
    std::array<float, 3> center_delta{};
    float maximum = 0;
    for (std::size_t i = 0; i < 3; ++i) {
        center_delta[i] = std::abs(stored(static_cast<double>(owner.center[i]) - target.center[i]));
        maximum = std::max(maximum, center_delta[i]);
    }

    unsigned axis = 0;
    bool flip = false;
    const bool near = maximum <= 15.0f;
    if (near) {
        std::array<float, 3> penetration{};
        for (std::size_t i = 0; i < 3; ++i)
            penetration[i] = stored(static_cast<double>(basis.half_extents[i]) - std::abs(projection[i]));
        if (!(penetration[1] <= penetration[0] || penetration[2] <= penetration[0]))
            axis = 0;
        else if (penetration[2] <= penetration[1])
            axis = 2;
        else
            axis = 1;
        flip = side ? projection[axis] > 0 : projection[axis] < 0;
    } else {
        std::array<std::array<float, 3>, 3> axes = basis.axes;
        const std::array<bool, 3> flips = side
            ? std::array<bool, 3>{projection[0] > 0, projection[1] > 0, projection[2] > 0}
            : std::array<bool, 3>{projection[0] >= 0, projection[1] < 0, projection[2] < 0};
        for (std::size_t i = 0; i < 3; ++i)
            if (flips[i]) for (auto& value : axes[i]) value = -value;
        std::array<float, 3> dots{};
        for (std::size_t i = 0; i < 3; ++i) {
            double dot = 0;
            for (std::size_t k = 0; k < 3; ++k)
                dot += static_cast<double>(axes[i][k]) * other.center[k];
            dots[i] = stored(dot);
        }
        if (std::abs(dots[1]) < std::abs(dots[0]) && std::abs(dots[2]) < std::abs(dots[0]))
            axis = 0;
        else if (std::abs(dots[1]) <= std::abs(dots[2]))
            axis = 2;
        else
            axis = 1;
        return {axes[axis], axis, false};
    }
    auto normal = basis.axes[axis];
    if (flip) for (auto& value : normal) value = -value;
    return {normal, axis, true};
}
} // namespace mco
