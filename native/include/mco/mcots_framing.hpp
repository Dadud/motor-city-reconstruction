#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

namespace mco {

inline constexpr std::uint32_t mcots_marker = 0x434d4f54;
inline constexpr std::size_t mcots_header_size = 11;
inline constexpr std::size_t mcots_maximum_payload = 65526;

struct McotsHeader {
    const std::uint32_t transaction_value;
    const std::uint8_t flags;
    bool operator==(const McotsHeader&) const = default;
};

struct McotsFrame {
    McotsHeader header;
    std::vector<std::uint8_t> payload;
    bool operator==(const McotsFrame&) const = default;
};

// Ordinary TCP envelope recovered from sender 0x6f7f20. Payload bytes must
// already be transformed; flags remain opaque and are preserved exactly.
// Neither function implements compression, encryption, transport, or login.
// Invalid/empty payloads and malformed complete frames throw invalid_argument.
[[nodiscard]] std::vector<std::uint8_t> encode_mcots_frame(
    McotsHeader header, std::span<const std::uint8_t> payload);
[[nodiscard]] McotsFrame decode_mcots_frame(std::span<const std::uint8_t> wire);

} // namespace mco
