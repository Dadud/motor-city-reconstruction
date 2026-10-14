#include "mco/lobby_channel_wait.hpp"

#include <iostream>
#include <stdexcept>
#include <utility>
#include <vector>

int main() {
    int failures = 0;
    const auto check = [&](bool condition) { if (!condition) ++failures; };
    using Event = std::pair<int, std::uintptr_t>;
    struct Case {
        mco::ChannelReplyWaitSlot slot{true, true, 0x9999};
        std::vector<Event> events;
        mco::ChannelWaitResult result{};
    };
    const auto run = [&](int reply_at, bool null_reply, bool completed,
                         int cancel_value, int disconnect_at, bool has_cancel = true) {
        Case sample;
        int polls = 0;
        mco::ChannelWaitBoundaries boundaries;
        boundaries.sleep_microseconds = [&](std::uint32_t value) {
            ++polls;
            sample.events.emplace_back(0, value);
            if (polls == reply_at) {
                sample.slot.reply = null_reply ? 0 : 0x1234;
                sample.slot.completed = completed;
            }
        };
        boundaries.is_connected = [&] {
            sample.events.emplace_back(2, polls);
            return disconnect_at < 0 || polls < disconnect_at;
        };
        if (has_cancel) boundaries.cancel = [&] {
            sample.events.emplace_back(1, polls);
            return cancel_value;
        };
        boundaries.release_reply = [&](std::uintptr_t token) {
            check(!sample.slot.waiting);
            sample.events.emplace_back(3, token);
        };
        sample.result = mco::wait_for_channel_reply(sample.slot, boundaries);
        return sample;
    };
    auto sample = run(1, false, true, 0, -1);
    check(sample.result == mco::ChannelWaitResult{0, 1});
    check(sample.events == std::vector<Event>{{0,250000},{1,1},{2,1}});
    check(!sample.slot.waiting && sample.slot.completed && sample.slot.reply == 0x1234);
    sample = run(1, true, true, 0, -1, false);
    check(sample.result == mco::ChannelWaitResult{-1, 1});
    sample = run(81, false, true, 0, -1);
    check(sample.result == mco::ChannelWaitResult{-2, 81});
    check(sample.events.size() == 243);
    check(sample.events[sample.events.size() - 3] == Event{0,250000});
    check(sample.events[sample.events.size() - 2] == Event{2,81});
    check(sample.events.back() == Event{3,0x1234});
    check(!sample.slot.waiting && sample.slot.completed && sample.slot.reply == 0);
    for (int value : {-1, 0, 2}) {
        sample = run(2, false, true, value, -1);
        check(sample.result == mco::ChannelWaitResult{0,2});
    }
    sample = run(1, false, true, 1, -1);
    check(sample.result == mco::ChannelWaitResult{-51,1});
    check(sample.events.back() == Event{3,0x1234});
    for (int tick : {1,81}) {
        sample = run(tick, false, true, 0, tick);
        check(sample.result == mco::ChannelWaitResult{-6,static_cast<std::uint32_t>(tick)});
        check(sample.slot.waiting && sample.slot.completed && sample.slot.reply == 0x1234);
        check(sample.events.back() == Event{2,static_cast<std::uintptr_t>(tick)});
    }
    sample = run(1, false, true, 1, 1);
    check(sample.result == mco::ChannelWaitResult{-6,1});
    check(sample.slot.waiting && sample.slot.reply == 0x1234);
    sample = run(1, false, false, 0, -1);
    check(sample.result == mco::ChannelWaitResult{-2,81});
    check(!sample.slot.completed && !sample.slot.waiting && !sample.slot.reply);
    sample = run(-1, false, false, 1, -1);
    check(!sample.slot.completed && !sample.slot.reply);
    mco::ChannelReplyWaitSlot slot{true,true,0x9999};
    try {
        (void)mco::wait_for_channel_reply(slot, {});
        ++failures;
    } catch (const std::invalid_argument&) {}
    check(slot.reply == 0x9999 && slot.completed && slot.waiting);
    mco::ChannelWaitBoundaries throwing;
    throwing.sleep_microseconds = [&](auto) { slot.reply = 0x1234; throw std::runtime_error("boundary"); };
    throwing.is_connected = [] { return true; };
    try {
        (void)mco::wait_for_channel_reply(slot, throwing);
        ++failures;
    } catch (const std::runtime_error&) {}
    check(slot.reply == 0x1234 && !slot.completed && slot.waiting);
    throwing.sleep_microseconds = [&](auto) { slot.reply = 0x1234; slot.completed = true; };
    throwing.cancel = [] { return 1; };
    throwing.release_reply = [&](auto token) {
        check(token == 0x1234 && !slot.waiting);
        throw std::runtime_error("release boundary");
    };
    try {
        (void)mco::wait_for_channel_reply(slot, throwing);
        ++failures;
    } catch (const std::runtime_error&) {}
    check(slot.reply == 0x1234 && slot.completed && !slot.waiting);
    if (failures) std::cerr << failures << " channel wait checks failed\n";
    return failures ? 1 : 0;
}
