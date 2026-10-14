#pragma once

#include "mco/lobby_channel_codec.hpp"
#include <array>
#include <span>

namespace mco {

inline constexpr std::size_t channel_argument_size = 0x15c;
inline constexpr std::size_t channel_allocation_size = 0x3bc;
using ChannelImage = std::array<std::uint8_t, channel_allocation_size>;
using ChannelRecord = std::array<std::uint8_t, channel_record_size>;

// Private reconstruction boundary, not a public mod API. Reproduces bounded
// constructor data writes; caller must supply the complete allocation image.
// Preserves holes and excludes host vtable/critical-section initialization.
// Throws invalid_argument if either span has the wrong exact size.
[[nodiscard]] ChannelImage initialize_channel_image(
    std::span<const std::uint8_t> argument,
    std::span<const std::uint8_t> allocated_image);

// Field copies at 0x7398a7..0x739a0e. Connection/caller overrides must already
// be present. Returns only the 0x1a4-byte serializer record, preserving holes.
[[nodiscard]] ChannelRecord materialize_channel_record(
    std::span<const std::uint8_t> channel_image);

} // namespace mco
