#pragma once

#include "mco/room_settings.hpp"
#include <optional>

namespace mco {
std::vector<std::uint8_t> initialize_room_settings(std::span<const std::uint8_t> image);
enum class RoomSelectionSource : std::uint32_t { active, defaults, cache };
struct RoomSelection {
    std::vector<std::uint8_t> room_image;
    std::int32_t result;
    RoomSelectionSource source;
};

// Cached settings are a caller-observed lookup result, not a server reply.
// Active rooms ignore the cache and compare names exactly. No task is queued.
RoomSelection select_room(std::span<const std::uint8_t> room_image,
                          std::span<const std::uint8_t> name,
                          std::optional<std::span<const std::uint8_t>> cached_settings = std::nullopt);
} // namespace mco
