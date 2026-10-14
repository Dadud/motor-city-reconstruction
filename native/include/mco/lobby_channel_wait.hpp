#pragma once

#include <cstdint>
#include <functional>

namespace mco {

inline constexpr std::uint32_t channel_poll_microseconds = 250000;
inline constexpr std::uint32_t channel_max_callback_polls = 80;

// Portable single-owner reply slot. The token is opaque data, never dereferenced.
// The listener/connection owner must serialize requests and retire disconnected
// slots. This type provides no synchronization or socket ownership by itself.
struct ChannelReplyWaitSlot {
    bool waiting = false;
    bool completed = false;
    std::uintptr_t reply = 0;
};

struct ChannelWaitBoundaries {
    // Both required. No implicit host sleep or connection lookup is performed.
    std::function<void(std::uint32_t)> sleep_microseconds;
    std::function<bool()> is_connected;
    std::function<std::int32_t()> cancel;
    std::function<void(std::uintptr_t)> release_reply;
};

struct ChannelWaitResult {
    std::int32_t code;
    std::uint32_t polls;
    bool operator==(const ChannelWaitResult&) const = default;
};

// Original 0x73a360 ordering. Resets old fields without releasing the old token.
// Disconnect retains pending fields; timeout/cancellation release then clear.
// Callback exceptions propagate with the state reached at that boundary.
[[nodiscard]] ChannelWaitResult wait_for_channel_reply(
    ChannelReplyWaitSlot& slot, const ChannelWaitBoundaries& boundaries);

} // namespace mco
