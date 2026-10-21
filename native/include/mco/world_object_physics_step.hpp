#pragma once
#include <cstdint>
#include <functional>
#include <span>

namespace mco {
inline constexpr std::size_t world_object_record_size = 0x4f8;
using WorldObjectPhysicsChild = std::function<void(std::span<std::uint8_t>)>;

void step_world_object_physics(
    std::span<std::uint8_t> record, bool mode_active, std::uint32_t mode_number,
    const WorldObjectPhysicsChild& environment_step,
    const WorldObjectPhysicsChild& contact_force_step);
}
