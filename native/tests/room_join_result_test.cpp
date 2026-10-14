#include "mco/room_join_result.hpp"

#include <algorithm>
#include <iostream>
#include <limits>
#include <stdexcept>

int main() {
    int failures = 0;
    const auto check = [&](bool condition) { if (!condition) ++failures; };
    const auto rejects = [&](auto action) {
        try { action(); ++failures; } catch (const std::invalid_argument&) {}
    };
    const std::vector<std::uint8_t> image(mco::room_worker_min_size+32,0xa5);
    for (const auto result : {std::numeric_limits<std::int32_t>::min(),-51,-1,0,1,
                              std::numeric_limits<std::int32_t>::max()}) {
        const auto transition = mco::apply_room_join_result(image,result);
        auto expected = image;
        const auto put = [&](std::size_t offset, std::uint32_t value) {
            for (std::size_t i = 0; i < 4; ++i)
                expected[offset+i] = static_cast<std::uint8_t>(value >> (8*i));
        };
        put(0x3a8,0);
        if (result < 0) {
            put(0x3a4,static_cast<std::uint32_t>(result));
            check(transition.return_code == result && !transition.notification);
        } else {
            put(0xc0,static_cast<std::uint32_t>(result));
            expected[0xec] = 1;
            expected[0xed] = 0;
            check(transition.return_code == 0);
            check(transition.notification == mco::RoomJoinNotification{0x1fc,0xa5a5a5a5,
                                                                      static_cast<std::uint32_t>(result)});
        }
        check(transition.worker_image == expected);
    }
    const std::array<std::uint8_t,mco::channel_argument_size> argument{};
    const auto call = mco::room_join_call(image,argument);
    check(call.interface_token == 0xa5a5a5a5 && call.caller_value_1 == 0xa5a5a5a5
          && call.caller_value_2 == 0xa5a5a5a5 && call.argument == argument);
    rejects([&] { (void)mco::apply_room_join_result(std::span(image).first(mco::room_worker_min_size-1),0); });
    rejects([&] { (void)mco::room_join_call(image,std::span(argument).first(argument.size()-1)); });
    if (failures) std::cerr << failures << " room join result checks failed\n";
    return failures ? 1 : 0;
}
