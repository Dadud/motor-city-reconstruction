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
template<std::size_t N> std::array<double,N> values(const std::array<double,N>& input) {
    std::array<double,N> output{};
    for (std::size_t i=0;i<N;++i) output[i]=stored(input[i]);
    return output;
}
std::array<double,3> transform(const std::array<double,3>& v,const std::array<double,9>& m) {
    std::array<double,3> result{};
    for (std::size_t i=0;i<3;++i) result[i]=stored((v[0]*m[i]+v[1]*m[i+3])+v[2]*m[i+6]);
    return result;
}
} // namespace

ImpulseMotion impulse_motion(const CollisionInertia& body,
                             const std::array<double,3>& impulse_input,
                             const std::array<double,3>& lever_input,
                             const std::array<double,3>& radial_input) {
    const auto p=values(impulse_input), lever=values(lever_input), radial=values(radial_input);
    const double inverse_mass=stored(body.inverse_mass);
    const auto inertia=values(body.inverse_inertia);
    const auto world_to_body=values(body.world_to_body), body_to_world=values(body.body_to_world);
    const double approach_extended=-((p[0]*radial[0]+p[1]*radial[1])+p[2]*radial[2]);
    const double approach=stored(approach_extended);
    ImpulseMotion result{};
    if (approach_extended>0) {
        const double inverse_length=1.0/std::sqrt((p[0]*p[0]+p[1]*p[1])+p[2]*p[2]);
        for (std::size_t i=0;i<3;++i) result.linear[i]=stored(static_cast<double>(stored(p[i]*inverse_length))*inverse_mass*approach);
    }
    const std::array<double,3> cross{stored(lever[1]*p[2]-lever[2]*p[1]),
        stored(lever[2]*p[0]-lever[0]*p[2]),stored(lever[0]*p[1]-lever[1]*p[0])};
    auto local=transform(cross,world_to_body);
    for (std::size_t i=0;i<3;++i) local[i]=stored(local[i]*inertia[i]);
    const auto angular=transform(local,body_to_world);
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
