#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

namespace mco {
inline constexpr std::size_t room_settings_min_size = 0x15a;
inline constexpr std::size_t room_settings_offset = 0xa0;

// Bounded private-image assignment. Copies terminated strings and observed
// fields while preserving all other destination bytes. No settings defaults,
// connection ownership or live room operations are inferred by this helper.
std::vector<std::uint8_t> apply_room_settings(std::span<const std::uint8_t> room_image,
                                           std::span<const std::uint8_t> settings_image);
} // namespace mco
