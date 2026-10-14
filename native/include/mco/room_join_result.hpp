#pragma once

#include "mco/lobby_channel_record.hpp"
#include <cstdint>
#include <optional>
#include <vector>

namespace mco {

inline constexpr std::size_t room_worker_min_size = 0x3b8;

struct RoomJoinCall {
    std::uint32_t interface_token;
    std::array<std::uint8_t,channel_argument_size> argument;
    std::uint32_t caller_value_1;
    std::uint32_t caller_value_2;
};

struct RoomJoinNotification {
    std::uint32_t owner_offset;
    std::uint32_t correlation_value;
    std::uint32_t channel_value;
    bool operator==(const RoomJoinNotification&) const = default;
};

struct RoomJoinTransition {
    std::vector<std::uint8_t> worker_image;
    std::int32_t return_code;
    std::optional<RoomJoinNotification> notification;
};

// Offsets use 0x44eba0's ECX base, not the worker interface at base+12.
// Pure private image boundary: no host token dereferencing or helper execution.
[[nodiscard]] RoomJoinCall room_join_call(std::span<const std::uint8_t> worker_image,
                                        std::span<const std::uint8_t> argument);
[[nodiscard]] RoomJoinTransition apply_room_join_result(
    std::span<const std::uint8_t> worker_image, std::int32_t native_result);

} // namespace mco
