#pragma once

#include "mco/lobby_channel_record.hpp"
#include <optional>
#include <vector>

namespace mco {

// Private data model from original 0x44cf80, not a stable mod API.
struct RoomJoinInputs {
    std::uint32_t server_selector;
    std::uint32_t protocol;
    std::uint32_t channel_id;
    std::vector<std::uint8_t> name;
    std::uint16_t max_ready;
    std::array<std::uint8_t,256> opaque_data;
};

// Extract observed fields only. Image covers at least 0x3a0 bytes and at most
// 65536; source name requires NUL within its original 32-byte field.
[[nodiscard]] RoomJoinInputs room_join_inputs_from_image(
    std::span<const std::uint8_t> room_image);

// Constructs a cleared 0x15c-byte argument. Names <=31, passwords <=16,
// neither with embedded NUL. Waiting requires an explicitly supplied owner
// token. Original callback/token remain inert research-image data, never called.
[[nodiscard]] std::array<std::uint8_t,channel_argument_size> build_room_join_argument(
    const RoomJoinInputs& inputs, std::span<const std::uint8_t> password = {},
    bool flag_0x20 = false, bool wait_for_completion = false,
    std::optional<std::uint32_t> owner_token = std::nullopt);

} // namespace mco
