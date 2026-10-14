#include "mco/room_disconnect_flow.hpp"

#include <algorithm>
#include <limits>
#include <stdexcept>

namespace {
using Kind = mco::RoomDisconnectActionKind;
void check(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
void put(std::vector<std::uint8_t>& image, std::size_t offset, std::uint32_t value, std::size_t size = 4) {
    for (std::size_t i = 0; i < size; ++i) image[offset + i] = static_cast<std::uint8_t>(value >> (8 * i));
}
std::vector<std::uint8_t> image(std::uint32_t connected = 1, std::uint32_t pending = 0) {
    std::vector<std::uint8_t> result(0x3c0, 0xa5);
    put(result, 0xec, connected, 2); put(result, 0x3a8, pending);
    put(result, 0x39c, 7); put(result, 0xc0, 99);
    return result;
}
template<class F> void reject(F function) {
    bool rejected = false;
    try { function(); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "invalid flow observation accepted");
}
mco::RoomDisconnectFlow ready(bool wait = true) {
    const auto source = image();
    mco::RoomDisconnectFlow flow(source, wait);
    check(flow.action().kind == Kind::reset_container && flow.action().owner_offset == 0x2e0, "first reset mismatch");
    flow.container_reset(source);
    check(flow.action().kind == Kind::reset_container && flow.action().owner_offset == 0x1fc, "second reset mismatch");
    flow.container_reset(source);
    check(flow.action().kind == Kind::enqueue && flow.action().owner_offset == 12, "enqueue action mismatch");
    check(flow.action().argument == std::array<std::uint8_t,8>{7,0,0,0,99,0,0,0}, "disconnect arguments mismatch");
    check(flow.room_image()[0xec] == 0 && flow.room_image()[0xed] == 0, "settings not reset before enqueue");
    return flow;
}
} // namespace

int main() {
    const auto pending_image = image(1, 1);
    mco::RoomDisconnectFlow pending(pending_image, true);
    pending.container_reset(pending_image); pending.container_reset(pending_image);
    check(pending.action().kind == Kind::yield_pending, "connected pending did not yield");
    pending.pending_yielded(image(0, 1));
    check(pending.action().kind == Kind::yield_pending, "connected was rechecked before pending cleared");
    pending.pending_yielded(image(0, 0));
    check(pending.action().kind == Kind::complete && pending.action().result == 0, "pending-cleared disconnected return mismatch");
    const auto disconnected_image = image(0, 9);
    mco::RoomDisconnectFlow disconnected(disconnected_image, true);
    disconnected.container_reset(disconnected_image); disconnected.container_reset(disconnected_image);
    check(disconnected.action().kind == Kind::complete && disconnected.action().result == 0,
          "disconnected pending waited or enqueued");
    check(disconnected.room_image()[0x3a8] == 9, "pending field changed");
    auto tracked = ready();
    tracked.enqueued(0xffffffffu);
    check(tracked.action().kind == Kind::query_completion && tracked.action().operation_id == 0xffffffffu,
          "tracked completion was not queried first");
    tracked.completion_queried(std::nullopt);
    check(tracked.action().kind == Kind::pump_application, "missing completion did not request pump");
    tracked.application_pumped(0);
    check(tracked.action().kind == Kind::query_completion, "successful pump did not return to query");
    tracked.completion_queried(-6);
    check(tracked.action().kind == Kind::complete && tracked.action().result == -6, "signed completion changed");
    for (auto result : {-1,1,std::numeric_limits<std::int32_t>::min(),std::numeric_limits<std::int32_t>::max()}) {
        auto aborted = ready(); aborted.enqueued(2); aborted.completion_queried(std::nullopt);
        const std::vector<std::uint8_t> before(aborted.room_image().begin(), aborted.room_image().end());
        aborted.application_pumped(result);
        check(aborted.action().kind == Kind::complete && aborted.action().result == -51, "application abort mapping mismatch");
        check(std::equal(before.begin(), before.end(), aborted.room_image().begin()), "abort changed room image");
        reject([&] { aborted.completion_queried(0); });
    }
    auto untracked = ready(false); untracked.enqueued();
    check(untracked.action().kind == Kind::complete && untracked.action().result == 0, "untracked enqueue did not finish immediately");
    auto invalid = ready();
    reject([&] { invalid.enqueued(); }); reject([&] { invalid.enqueued(0); });
    check(invalid.action().kind == Kind::enqueue, "invalid operation ID changed phase");
    reject([&] { invalid.container_reset(image()); });
    reject([&] { invalid.application_pumped(0); });
    mco::RoomDisconnectFlow observe(image(), true);
    const auto before = std::vector<std::uint8_t>(observe.room_image().begin(), observe.room_image().end());
    reject([&] { observe.container_reset(std::vector<std::uint8_t>(0x3ab)); });
    reject([&] { observe.container_reset(std::vector<std::uint8_t>(0x3c1)); });
    check(observe.action().owner_offset == 0x2e0 && std::equal(before.begin(), before.end(), observe.room_image().begin()),
          "invalid observed image changed request or image");
    reject([] { mco::RoomDisconnectFlow flow(std::vector<std::uint8_t>(65537), true); });
    observe.container_reset(observe.room_image());
    check(observe.action().owner_offset == 0x1fc, "aliased read-only observation failed");
}
