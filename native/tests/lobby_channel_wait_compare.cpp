#include "mco/lobby_channel_wait.hpp"

#include <array>
#include <iostream>
#include <limits>
#include <utility>
#include <vector>

// Private synthetic scenario protocol (seven integer fields): reply tick,
// null reply, incomplete reply, cancellation tick/value, disconnect tick,
// callback present. -1 means no scheduled event. No host sleep or sockets.
int main() {
    std::array<std::int64_t, 7> values{};
    for (auto& value : values) if (!(std::cin >> value)) return 2;
    std::cin >> std::ws;
    if (std::cin.peek() != std::char_traits<char>::eof()) return 2;
    for (auto index : {0,3,5})
        if (values[index] < -1 || values[index] > 81) return 2;
    for (auto index : {1,2,6})
        if (values[index] != 0 && values[index] != 1) return 2;
    if (values[4] < std::numeric_limits<std::int32_t>::min()
        || values[4] > std::numeric_limits<std::int32_t>::max()) return 2;
    mco::ChannelReplyWaitSlot slot{true, true, 0x9999};
    std::vector<std::pair<int,std::uintptr_t>> events;
    std::uint32_t polls = 0;
    mco::ChannelWaitBoundaries boundaries;
    boundaries.sleep_microseconds = [&](std::uint32_t value) {
        ++polls;
        events.emplace_back(0,value);
        if (polls == values[0]) {
            slot.reply = values[1] ? 0 : 0x1234;
            slot.completed = !values[2];
        }
    };
    boundaries.is_connected = [&] {
        events.emplace_back(2,polls);
        return values[5] < 0 || polls < values[5];
    };
    if (values[6]) boundaries.cancel = [&] {
        events.emplace_back(1,polls);
        return polls == values[3] ? static_cast<std::int32_t>(values[4]) : 0;
    };
    boundaries.release_reply = [&](std::uintptr_t token) { events.emplace_back(3,token); };
    const auto result = mco::wait_for_channel_reply(slot,boundaries);
    std::cout << "{\"code\":" << result.code << ",\"polls\":" << result.polls
        << ",\"waiting\":" << (slot.waiting ? "true" : "false")
        << ",\"completed\":" << (slot.completed ? "true" : "false")
        << ",\"reply\":" << slot.reply << ",\"events\":[";
    bool first = true;
    for (const auto& [kind,value] : events) {
        if (!first) std::cout << ',';
        first = false;
        std::cout << '[' << kind << ',' << value << ']';
    }
    std::cout << "]}\n";
    return std::cout ? 0 : 2;
}
