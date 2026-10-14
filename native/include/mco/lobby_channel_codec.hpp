#pragma once
#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

namespace mco {
inline constexpr std::size_t channel_record_size = 0x1a4;
inline constexpr std::size_t channel_payload_limit = 0x170;
// Native layout at serializer 0x7e4c30; opaque fields retain their bit patterns.
// Throws invalid_argument on invalid size, unterminated strings or capacity.
[[nodiscard]] std::vector<std::uint8_t> encode_channel_join_payload(
    std::span<const std::uint8_t> native_record);
struct ChannelJoinSuccess {
    std::uint16_t message_id;
    std::uint32_t channel_id;
    std::uint32_t value_2;
    bool operator==(const ChannelJoinSuccess&) const = default;
};
// Body only, after the existing lobby envelope has been decoded.
[[nodiscard]] ChannelJoinSuccess decode_channel_join_success(
    std::uint16_t message_id, std::span<const std::uint8_t> body);
}
