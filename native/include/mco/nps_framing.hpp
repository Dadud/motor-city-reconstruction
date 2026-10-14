#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

namespace mco {

inline constexpr std::size_t nps_max_frame_bytes = 65535;

struct NpsFrame {
    std::uint16_t message_id;
    std::vector<std::uint8_t> body;
    bool operator==(const NpsFrame&) const = default;
};

struct NpsMessageHeader {
    std::uint16_t message_id;
    std::uint16_t length;
    std::uint16_t flags;
    std::uint16_t reserved;
    std::uint32_t auxiliary;
    bool operator==(const NpsMessageHeader&) const = default;
};

[[nodiscard]] std::uint16_t nps_native_flags(std::uint16_t message_id) noexcept;
// Plain prefix and body only. No cipher, socket, or payload interpretation.
[[nodiscard]] std::vector<std::uint8_t> encode_nps_frame(const NpsFrame& frame);
// Header-enabled serializer 0x7e0800. Auxiliary is caller supplied; its
// protocol meaning must be recovered for each message before sending it.
[[nodiscard]] std::vector<std::uint8_t> encode_nps_message(
    std::uint16_t message_id, std::span<const std::uint8_t> payload = {},
    std::uint32_t auxiliary = 0);
// Explicit interpretation: valid four-byte frames have no message header.
[[nodiscard]] NpsMessageHeader nps_message_header(const NpsFrame& frame);

class NpsFrameDecoder {
public:
    // Keeps only one incomplete frame, bounded by the uint16 wire length.
    // Malformed length permanently fails this decoder; discard the connection.
    [[nodiscard]] std::vector<NpsFrame> feed(std::span<const std::uint8_t> data);
    // EOF check. Throws invalid_argument for a failed decoder or partial frame.
    void finish() const;
private:
    std::vector<std::uint8_t> pending_;
    bool failed_ = false;
};

} // namespace mco
