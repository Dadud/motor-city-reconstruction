#include "mco/lobby_channel_close.hpp"

#include <limits>
#include <stdexcept>

namespace {
void check(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
template<class F> void reject(F function) {
    bool rejected = false;
    try { function(); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "wide channel-close input was narrowed without validation");
}
} // namespace

int main() {
    check(mco::native_close_arguments(0x12345678, 0x87654321) ==
          std::array<std::uint8_t,8>{0x78,0x56,0x34,0x12,0x21,0x43,0x65,0x87}, "local pair endianness mismatch");
    const mco::ChannelCloseRequest request{0x87654321};
    check(request.channel_id() == 0x87654321 && request.payload() == std::array<std::uint8_t,4>{0x87,0x65,0x43,0x21},
          "payload ID or endianness mismatch");
    check(mco::encode_nps_frame(request.frame()) == std::vector<std::uint8_t>{1,5,0,8,0x87,0x65,0x43,0x21},
          "plain 0x105 frame mismatch");
    check(mco::native_close_arguments(44, 0) == std::array<std::uint8_t,8>{44,0,0,0,0,0,0,0}, "zero local channel was rejected");
    check(mco::encode_nps_frame(mco::ChannelCloseRequest{0}.frame()) == std::vector<std::uint8_t>{1,5,0,8,0,0,0,0},
          "raw zero frame was replaced by interface policy");
    check(mco::ChannelCloseRequest{0xffffffffu}.payload() == std::array<std::uint8_t,4>{255,255,255,255}, "uint32 boundary mismatch");
    const auto first = mco::ChannelCloseRequest{7}.frame();
    // Selector variation affects the local arguments, never the packet shape.
    for (auto selector : {0u,44u,0x80000000u,0xffffffffu}) {
        const auto arguments = mco::native_close_arguments(selector, 7);
        check(arguments[4] == 7 && mco::ChannelCloseRequest{7}.frame() == first, "selector leaked into wire codec");
    }
    for (auto value : {std::uint64_t{0x100000000}, std::numeric_limits<std::uint64_t>::max()}) {
        reject([&] { mco::ChannelCloseRequest{value}; });
        reject([&] { mco::native_close_arguments(value, 1); });
        reject([&] { mco::native_close_arguments(1, value); });
    }
}
