#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <stdexcept>
#include <vector>

namespace mco {
inline constexpr std::size_t room_disconnect_min_size = 0x3ac;

class PendingRoomOperation : public std::invalid_argument {
public:
    PendingRoomOperation();
};

struct RoomDisconnectPreparation {
    std::vector<std::uint8_t> room_image;
    std::optional<std::array<std::uint8_t, 8>> argument;
    bool tracked;
    std::optional<std::int32_t> immediate_return;
    std::array<std::uint32_t, 2> reset_owner_offsets{0x2e0, 0x1fc};
    std::optional<std::uint32_t> task_kind() const;
};

// Stable-state preparation only. Resets and enqueue are intents; pending waits
// and actual server disconnection are excluded. No unspecified task bytes are
// synthesized beyond the initialized task kind and eight-byte argument.
RoomDisconnectPreparation prepare_room_disconnect(std::span<const std::uint8_t> room_image,
                                                  bool wait_for_completion);
} // namespace mco
