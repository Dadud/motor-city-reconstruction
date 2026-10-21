#pragma once
#include <cstdint>
#include <functional>
#include <vector>

namespace mco {
inline constexpr std::uint32_t world_object_stride = 0x4f8;

void update_active_world_objects(
    std::uint32_t base_address, const std::vector<bool>& active_flags,
    const std::function<void(std::uint32_t)>& update_object);
}
