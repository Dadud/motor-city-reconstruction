#include "mco/collision_impulse.hpp"
#include <cmath>
#include <limits>
#include <stdexcept>

namespace mco {
namespace {
float stored(double value) {
    if (!std::isfinite(value) || std::abs(value)>std::numeric_limits<float>::max())
        throw std::invalid_argument("finite float32 collision input required");
    return static_cast<float>(value);
}
float ieee_float(double value) { return static_cast<float>(value); }
float rounded(double value, bool allow_nonfinite) {
    return allow_nonfinite ? ieee_float(value) : stored(value);
}
template<std::size_t N> std::array<double,N> values(const std::array<double,N>& input,
                                                     bool allow_nonfinite = false) {
    std::array<double,N> output{};
    for (std::size_t i=0;i<N;++i) output[i]=rounded(input[i], allow_nonfinite);
    return output;
}
std::array<double,3> transform(const std::array<double,3>& v,const std::array<double,9>& m,
                               bool allow_nonfinite = false) {
    std::array<double,3> result{};
    for (std::size_t i=0;i<3;++i) result[i]=rounded((v[0]*m[i]+v[1]*m[i+3])+v[2]*m[i+6],
                                                    allow_nonfinite);
    return result;
}
} // namespace

ImpulseMotion impulse_motion(const CollisionInertia& body,
                             const std::array<double,3>& impulse_input,
                             const std::array<double,3>& lever_input,
                             const std::array<double,3>& radial_input,
                             bool allow_nonfinite) {
    const auto p=values(impulse_input, allow_nonfinite),
               lever=values(lever_input, allow_nonfinite),
               radial=values(radial_input, allow_nonfinite);
    const double inverse_mass=rounded(body.inverse_mass, allow_nonfinite);
    const auto inertia=values(body.inverse_inertia, allow_nonfinite);
    const auto world_to_body=values(body.world_to_body, allow_nonfinite),
               body_to_world=values(body.body_to_world, allow_nonfinite);
    const double approach_extended=-((p[0]*radial[0]+p[1]*radial[1])+p[2]*radial[2]);
    const double approach=rounded(approach_extended, allow_nonfinite);
    ImpulseMotion result{};
    if (approach_extended>0) {
        const double inverse_length=1.0/std::sqrt((p[0]*p[0]+p[1]*p[1])+p[2]*p[2]);
        for (std::size_t i=0;i<3;++i) result.linear[i]=rounded(static_cast<double>(rounded(p[i]*inverse_length, allow_nonfinite))*inverse_mass*approach, allow_nonfinite);
    }
    const std::array<double,3> cross{rounded(lever[1]*p[2]-lever[2]*p[1], allow_nonfinite),
        rounded(lever[2]*p[0]-lever[0]*p[2], allow_nonfinite),
        rounded(lever[0]*p[1]-lever[1]*p[0], allow_nonfinite)};
    auto local=transform(cross,world_to_body, allow_nonfinite);
    for (std::size_t i=0;i<3;++i) local[i]=rounded(local[i]*inertia[i], allow_nonfinite);
    const auto angular=transform(local,body_to_world, allow_nonfinite);
    for (std::size_t i=0;i<3;++i) result.angular[i]=static_cast<float>(angular[i]);
    return result;
}

float plane_height(const std::array<double,3>& normal_input,
                   const std::array<double,3>& plane_point,
                   const std::array<double,3>& query_input) {
    const auto n=values(normal_input), p=values(plane_point), q=values(query_input);
    if (n[1]==0) throw std::invalid_argument("vertical plane has no unique height");
    return stored(-((q[2]-p[2])*n[2]+(q[0]-p[0])*n[0])/n[1]+p[1]);
}
} // namespace mco
