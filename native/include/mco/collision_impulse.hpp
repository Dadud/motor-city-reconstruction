#pragma once
#include <array>

namespace mco {
struct CollisionInertia {
    double inverse_mass;
    std::array<double,3> inverse_inertia;
    std::array<double,9> world_to_body;
    std::array<double,9> body_to_world;
};
struct ImpulseMotion { std::array<float,3> linear, angular; };
ImpulseMotion impulse_motion(const CollisionInertia& body,
                             const std::array<double,3>& impulse,
                             const std::array<double,3>& lever,
                             const std::array<double,3>& radial_direction);
float plane_height(const std::array<double,3>& normal,
                   const std::array<double,3>& plane_point,
                   const std::array<double,3>& query);
} // namespace mco
