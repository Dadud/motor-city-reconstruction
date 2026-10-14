#include "mco/room_disconnect.hpp"

#include <algorithm>
#include <stdexcept>

namespace {
void check(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
void put(std::vector<std::uint8_t>& bytes, std::size_t offset, std::uint32_t value, std::size_t size = 4) {
    for (std::size_t i = 0; i < size; ++i) bytes[offset + i] = static_cast<std::uint8_t>(value >> (8 * i));
}
std::vector<std::uint8_t> image(std::uint32_t connected, std::uint32_t pending = 0) {
    std::vector<std::uint8_t> bytes(0x3c0 + 23);
    for (std::size_t i = 0; i < bytes.size(); ++i) bytes[i] = static_cast<std::uint8_t>(i * 37 + 19);
    put(bytes, 0xec, connected, 2); put(bytes, 0x3a8, pending);
    put(bytes, 0x39c, 0xffffffffu); put(bytes, 0xc0, 0x80000000u);
    return bytes;
}
std::vector<std::uint8_t> expected_reset(std::vector<std::uint8_t> bytes) {
    for (const auto& [offset, count] : {std::pair<std::size_t,std::size_t>{0xa0,32}, {0xd0,16}, {0xf4,256},
         {0xc0,12}, {0x1f4,4}, {0xe2,2}, {0xec,2}, {0x1f8,2}, {0xe6,2}, {0xe8,4}, {0xf0,4}})
        std::fill_n(bytes.begin() + offset, count, std::uint8_t{0});
    put(bytes, 0xcc, 0x21); put(bytes, 0xe0, 2, 2); bytes[0xe4] = 1;
    return bytes;
}
template<class F> void reject(F function) {
    bool rejected = false;
    try { function(); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "unsafe disconnect image accepted");
}
} // namespace

int main() {
    for (auto pending : {0u, 5u, 0xffffffffu}) {
        const auto source = image(0, pending);
        for (auto wait : {false, true}) {
            const auto result = mco::prepare_room_disconnect(source, wait);
            check(!result.argument && !result.task_kind() && !result.tracked && result.immediate_return == 0,
                  "disconnected no-enqueue return mismatch");
            check(result.room_image == expected_reset(source), "disconnected reset or pending preservation mismatch");
        }
    }
    for (auto connected : {1u, 0xffffu}) {
        const auto source = image(connected);
        const auto original = source;
        for (auto wait : {false, true}) {
            const auto result = mco::prepare_room_disconnect(source, wait);
            const std::array<std::uint8_t, 8> argument{0xff,0xff,0xff,0xff,0,0,0,0x80};
            check(result.argument == argument && result.task_kind() == 1 && result.tracked == wait,
                  "initialized disconnect argument or tracking mismatch");
            check(wait ? !result.immediate_return : result.immediate_return == 0, "disconnect immediate return mismatch");
            check(result.room_image == expected_reset(source), "connected reset or unknown byte preservation mismatch");
            check(result.reset_owner_offsets == std::array<std::uint32_t,2>{0x2e0,0x1fc}, "container reset intents/order mismatch");
        }
        check(source == original, "source image modified");
    }
    for (auto wait : {false, true}) {
        bool pending_rejected = false;
        try { mco::prepare_room_disconnect(image(1, 1), wait); }
        catch (const mco::PendingRoomOperation&) { pending_rejected = true; }
        check(pending_rejected, "connected pending operation did not require observed completion");
    }
    const auto source = image(0);
    reject([&] { mco::prepare_room_disconnect(std::span<const std::uint8_t>{source}.first(0x3ab), false); });
    reject([&] { mco::prepare_room_disconnect(std::vector<std::uint8_t>(65537), false); });
    check(mco::prepare_room_disconnect(std::vector<std::uint8_t>(0x3ac), false).room_image.size() == 0x3ac,
          "minimum room size rejected");
    check(mco::prepare_room_disconnect(std::vector<std::uint8_t>(65536), true).room_image.size() == 65536,
          "maximum room size rejected");
}
