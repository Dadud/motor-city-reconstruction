#include "mco/lobby_channel_wait.hpp"

#include <stdexcept>

namespace mco {

ChannelWaitResult wait_for_channel_reply(
    ChannelReplyWaitSlot& slot, const ChannelWaitBoundaries& boundaries) {
    if (!boundaries.sleep_microseconds || !boundaries.is_connected)
        throw std::invalid_argument("channel wait requires sleep and connection boundaries");
    slot.reply = 0;
    slot.completed = false;
    slot.waiting = true;
    std::uint32_t polls = 0;
    for (;;) {
        if (slot.completed) {
            slot.waiting = false;
            return {slot.reply ? 0 : -1, polls};
        }
        boundaries.sleep_microseconds(channel_poll_microseconds);
        ++polls;
        std::int32_t code;
        if (polls > channel_max_callback_polls) {
            code = -2;
        } else if (boundaries.cancel && boundaries.cancel() == 1) {
            code = -51;
        } else {
            if (!boundaries.is_connected()) return {-6, polls};
            continue;
        }
        if (!boundaries.is_connected()) return {-6, polls};
        if (slot.reply) {
            slot.waiting = false;
            if (boundaries.release_reply) boundaries.release_reply(slot.reply);
            slot.reply = 0;
        }
        slot.waiting = false;
        return {code, polls};
    }
}

} // namespace mco
