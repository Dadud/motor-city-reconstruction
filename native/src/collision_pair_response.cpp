#include "mco/collision_pair_response.hpp"
#include "mco/collision_response.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <cstring>
#include <limits>
#include <stdexcept>

namespace mco {
namespace {
using V3 = std::array<float, 3>;
using D3 = std::array<double, 3>;

float f32(double value) {
    if (!std::isfinite(value) || std::abs(value) > std::numeric_limits<float>::max())
        throw std::invalid_argument("finite float32 collision input required");
    return static_cast<float>(value);
}
float native_round(double value) { return static_cast<float>(value); }
V3 add(const V3& a, const V3& b) {
    return {native_round(static_cast<double>(a[0]) + b[0]),
            native_round(static_cast<double>(a[1]) + b[1]),
            native_round(static_cast<double>(a[2]) + b[2])};
}
V3 subtract(const V3& a, const V3& b) {
    return {native_round(static_cast<double>(a[0]) - b[0]),
            native_round(static_cast<double>(a[1]) - b[1]),
            native_round(static_cast<double>(a[2]) - b[2])};
}
V3 scale(const V3& a, float value) {
    return {native_round(static_cast<double>(a[0]) * value),
            native_round(static_cast<double>(a[1]) * value),
            native_round(static_cast<double>(a[2]) * value)};
}
float dot(const V3& a, const V3& b) {
    return native_round((static_cast<double>(a[0]) * b[0] +
                         static_cast<double>(a[1]) * b[1]) +
                         static_cast<double>(a[2]) * b[2]);
}
V3 cross(const V3& a, const V3& b) {
    return {native_round(static_cast<double>(a[1]) * b[2] - static_cast<double>(a[2]) * b[1]),
            native_round(static_cast<double>(a[2]) * b[0] - static_cast<double>(a[0]) * b[2]),
            native_round(static_cast<double>(a[0]) * b[1] - static_cast<double>(a[1]) * b[0])};
}
V3 transform(const V3& v, const std::array<double, 9>& m) {
    return {native_round((static_cast<double>(v[0]) * m[0] + v[1] * m[3]) + v[2] * m[6]),
            native_round((static_cast<double>(v[0]) * m[1] + v[1] * m[4]) + v[2] * m[7]),
            native_round((static_cast<double>(v[0]) * m[2] + v[1] * m[5]) + v[2] * m[8])};
}
D3 widen(const V3& value) { return {value[0], value[1], value[2]}; }
V3 lever_for(const CollisionImpactBody& body, const V3& contact, V3& radial) {
    const V3 local = body.center_of_mass_local;
    V3 center_offset = transform(local, body.inertia.body_to_world);
    const V3 lever = subtract(subtract(contact, body.position), center_offset);
    const double squared = (static_cast<double>(lever[0]) * lever[0] +
                            static_cast<double>(lever[1]) * lever[1]) +
                            static_cast<double>(lever[2]) * lever[2];
    if (squared == 0.0) radial = {0.f, 0.f, 0.f};
    else {
        const double inverse_length = 1.0 / std::sqrt(squared);
        radial = {f32(lever[0] * inverse_length),
                  f32(lever[1] * inverse_length),
                  f32(lever[2] * inverse_length)};
    }
    return lever;
}
bool read_only(const CollisionImpactBody& owner, const CollisionImpactBody& target) {
    bool owner_gate = owner.mode != 0 && target.mode == 0;
    bool target_gate = target.mode != 0 && owner.mode == 0;
    if (target.peer_gate < owner.gate) owner_gate = true;
    if (owner.peer_gate < target.gate) target_gate = true;
    if (owner_gate && target_gate) owner_gate = target_gate = false;
    return owner_gate;
}
bool target_read_only(const CollisionImpactBody& owner, const CollisionImpactBody& target) {
    bool owner_gate = owner.mode != 0 && target.mode == 0;
    bool target_gate = target.mode != 0 && owner.mode == 0;
    if (target.peer_gate < owner.gate) owner_gate = true;
    if (owner.peer_gate < target.gate) target_gate = true;
    if (owner_gate && target_gate) owner_gate = target_gate = false;
    return target_gate;
}
void put_u32(std::array<std::uint8_t, 0x400>& bytes, std::size_t offset, std::uint32_t value) {
    for (unsigned i = 0; i < 4; ++i)
        bytes[offset + i] = static_cast<std::uint8_t>(value >> (i * 8));
}
void put_f32(std::array<std::uint8_t, 0x400>& bytes, std::size_t offset, float value) {
    put_u32(bytes, offset, std::bit_cast<std::uint32_t>(value));
}
void write_contact(CollisionImpactBody& body, std::uint32_t other,
                   const V3& point, const V3& normal_impulse,
                   const V3& tangential_impulse, int status, float approach,
                   float effective_mass) {
    put_u32(body.contact_record, 0x3c4, other);
    put_f32(body.contact_record, 0x3c8, std::abs(approach));
    for (std::size_t i = 0; i < 3; ++i) {
        put_f32(body.contact_record, 0x3cc + 4 * i, normal_impulse[i]);
        put_f32(body.contact_record, 0x3d8 + 4 * i, tangential_impulse[i]);
        put_f32(body.contact_record, 0x3e8 + 4 * i, point[i]);
    }
    put_u32(body.contact_record, 0x3e4, static_cast<std::uint32_t>(status));
    put_u32(body.contact_record, 0x3f4, 4);
    put_u32(body.contact_record, 0x3f8, 6);
    put_f32(body.contact_record, 0x3fc, effective_mass);
}
} // namespace

CollisionImpactResult resolve_pair_impulse(
    const CollisionImpactBody& owner_input,
    const CollisionImpactBody& target_input,
    const std::array<float, 3>& contact_input,
    const std::array<float, 3>& normal_input,
    float threshold_coefficient,
    float sliding_coefficient) {
    CollisionImpactBody owner = owner_input, target = target_input;
    const V3 contact = contact_input, normal = normal_input;
    V3 radial_owner{}, radial_target{};
    const V3 lever_owner = lever_for(owner, contact, radial_owner);
    const V3 lever_target = lever_for(target, contact, radial_target);
    const bool owner_gated = read_only(owner, target);
    const bool target_gated = target_read_only(owner, target);
    float effective_mass;
    if (!owner_gated && target_gated) effective_mass = owner.mass;
    else if (owner_gated && !target_gated) effective_mass = target.mass;
    else {
        const float product = f32(static_cast<double>(owner.mass) * target.mass);
        const float sum = f32(static_cast<double>(owner.mass) + target.mass);
        effective_mass = f32(static_cast<double>(product) / sum);
    }
    const float response_weight = f32((f32(owner.response_coefficient + target.response_coefficient) * .5f) + 1.f);

    V3 linear_owner{}, angular_owner{}, linear_target{}, angular_target{};
    V3 current_linear_owner = owner.linear_velocity, current_linear_target = target.linear_velocity;
    V3 current_angular_owner{}, current_angular_target{};
    for (std::size_t i = 0; i < 3; ++i) {
        current_angular_owner[i] = native_round(static_cast<double>(owner.angular_turn_velocity[i]) * 6.2831855);
        current_angular_target[i] = native_round(static_cast<double>(target.angular_turn_velocity[i]) * 6.2831855);
    }
    unsigned samples = 0;
    int status = 0;
    for (unsigned step = 0; step < 32; ++step) {
        const float time = f32(static_cast<double>(step) * .03125);
        const V3 point_velocity_owner = add(current_linear_owner, cross(current_angular_owner, lever_owner));
        const V3 point_velocity_target = add(current_linear_target, cross(current_angular_target, lever_target));
        const V3 relative = scale(subtract(point_velocity_owner, point_velocity_target), effective_mass);
        const float approach = dot(relative, normal);
        if (approach >= 0.f) break;
        const V3 normal_impulse = scale(normal, native_round(-approach));
        const auto response = tangential_response(widen(relative), widen(normal),
                                                  threshold_coefficient, sliding_coefficient,
                                                  true);
        status = response.status;
        const V3 tangent_impulse = response.vector;
        if (step == 0) {
            write_contact(owner, target.address, contact, normal_impulse, tangent_impulse,
                          status, approach, effective_mass);
            write_contact(target, owner.address, contact, scale(normal_impulse, -1.f),
                          scale(tangent_impulse, -1.f), status, approach, effective_mass);
        }
        const V3 normal_at_time = scale(normal_impulse, time);
        const V3 tangent_at_time = scale(tangent_impulse, time);
        auto update = [&](CollisionImpactBody& body, bool gated, const V3& lever,
                          const V3& radial, V3& current_linear, V3& current_angular,
                          V3& sum_linear, V3& sum_angular, float sign) {
            if (gated) return;
            const V3 signed_normal = scale(normal_at_time, sign);
            const V3 signed_tangent = scale(tangent_at_time, sign);
            const auto normal_motion = impulse_motion(body.inertia, widen(signed_normal),
                                                       widen(lever), widen(radial), true);
            const auto tangent_motion = impulse_motion(body.inertia, widen(signed_tangent),
                                                        widen(lever), widen(radial), true);
            current_linear = add(add(current_linear, tangent_motion.linear), normal_motion.linear);
            current_angular = add(add(current_angular, tangent_motion.angular), normal_motion.angular);
            for (std::size_t i = 0; i < 3; ++i) {
                sum_linear[i] = native_round(static_cast<double>(normal_motion.linear[i]) * response_weight + sum_linear[i]);
                sum_linear[i] = native_round(static_cast<double>(sum_linear[i]) + tangent_motion.linear[i]);
                sum_angular[i] = native_round(static_cast<double>(normal_motion.angular[i]) * response_weight + sum_angular[i]);
                sum_angular[i] = native_round(static_cast<double>(sum_angular[i]) + tangent_motion.angular[i]);
            }
            body.gate = 0.f;
        };
        update(owner, owner_gated, lever_owner, radial_owner, current_linear_owner,
               current_angular_owner, linear_owner, angular_owner, 1.f);
        update(target, target_gated, lever_target, radial_target, current_linear_target,
               current_angular_target, linear_target, angular_target, -1.f);
        ++samples;
    }
    if (samples != 0) {
        owner.linear_velocity = add(owner_input.linear_velocity, linear_owner);
        target.linear_velocity = add(target_input.linear_velocity, linear_target);
        owner.angular_turn_velocity = add(owner_input.angular_turn_velocity, scale(angular_owner, .15915494f));
        target.angular_turn_velocity = add(target_input.angular_turn_velocity, scale(angular_target, .15915494f));
    }
    return {samples != 0, owner, target, samples, status, effective_mass};
}

CollisionSurfaceImpactResult resolve_surface_impulse(
    const CollisionImpactBody& body_input,
    const std::array<float, 3>& contact_input,
    const std::array<float, 3>& normal_input,
    float threshold_coefficient,
    float sliding_coefficient) {
    CollisionImpactBody body = body_input;
    const V3 contact = contact_input, normal = normal_input;
    V3 radial{};
    const V3 lever = lever_for(body, contact, radial);
    const float mass = body.mass;
    const float response_weight = f32(static_cast<double>(body.response_coefficient) + 1.0);
    V3 linear_sum{}, angular_sum{};
    V3 current_linear = body.linear_velocity, current_angular{};
    for (std::size_t i = 0; i < 3; ++i)
        current_angular[i] = f32(static_cast<double>(body.angular_turn_velocity[i]) * 6.2831855);
    unsigned samples = 0;
    int status = 0;
    for (unsigned step = 0; step < 32; ++step) {
        const float time = f32(static_cast<double>(step) * .03125);
        const V3 point_velocity = add(current_linear, cross(current_angular, lever));
        const V3 relative = scale(point_velocity, mass);
        const float approach = dot(relative, normal);
        if (approach >= 0.f) break;
        const V3 normal_impulse = scale(normal, f32(-approach));
        const auto response = tangential_response(widen(relative), widen(normal),
                                                  threshold_coefficient, sliding_coefficient);
        status = response.status;
        const V3 tangent_impulse = response.vector;
        if (step == 0) {
            put_u32(body.contact_record, 0x3c4, 0);
            put_f32(body.contact_record, 0x3c8, std::abs(approach));
            for (std::size_t i = 0; i < 3; ++i) {
                put_f32(body.contact_record, 0x3cc + 4 * i, normal_impulse[i]);
                put_f32(body.contact_record, 0x3d8 + 4 * i, tangent_impulse[i]);
                put_f32(body.contact_record, 0x3e8 + 4 * i, contact[i]);
            }
            put_u32(body.contact_record, 0x3e4, static_cast<std::uint32_t>(status));
            put_u32(body.contact_record, 0x3f4, 2);
            put_u32(body.contact_record, 0x3f8, body.embedded_contact_pointer);
            put_f32(body.contact_record, 0x3fc, mass);
        }
        const auto normal_motion = impulse_motion(body.inertia,
            widen(scale(normal_impulse, time)), widen(lever), widen(radial));
        const auto tangent_motion = impulse_motion(body.inertia,
            widen(scale(tangent_impulse, time)), widen(lever), widen(radial));
        current_linear = add(add(current_linear, tangent_motion.linear), normal_motion.linear);
        current_angular = add(add(current_angular, tangent_motion.angular), normal_motion.angular);
        for (std::size_t i = 0; i < 3; ++i) {
            linear_sum[i] = f32(static_cast<double>(normal_motion.linear[i]) * response_weight + linear_sum[i]);
            linear_sum[i] = f32(static_cast<double>(linear_sum[i]) + tangent_motion.linear[i]);
            angular_sum[i] = f32(static_cast<double>(normal_motion.angular[i]) * response_weight + angular_sum[i]);
            angular_sum[i] = f32(static_cast<double>(angular_sum[i]) + tangent_motion.angular[i]);
        }
        ++samples;
    }
    if (samples != 0) {
        body.linear_velocity = add(body_input.linear_velocity, linear_sum);
        body.angular_turn_velocity = add(body_input.angular_turn_velocity,
                                         scale(angular_sum, .15915494f));
    }
    return {samples != 0, body, samples, status};
}
} // namespace mco
