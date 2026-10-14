#pragma once

#include "mco/nps_framing.hpp"
#include <array>

namespace mco {
// Wider inputs are checked before narrowing. The selector routes a local
// registry entry and never appears in the opcode 0x105 payload.
std::array<std::uint8_t, 8> native_close_arguments(std::uint64_t server_selector,
                                                 std::uint64_t channel_id);
class ChannelCloseRequest {
public:
    explicit ChannelCloseRequest(std::uint64_t channel_id);
    std::uint32_t channel_id() const noexcept;
    std::array<std::uint8_t, 4> payload() const noexcept;
    NpsFrame frame() const;
private:
    std::uint32_t channel_id_;
};
// Raw zero is encodable; deciding to ignore it belongs to the separately
// recovered close interface. This codec does not send, log off or remove state.
} // namespace mco
