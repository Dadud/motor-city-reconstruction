#include "mco/room_settings.hpp"

#include <algorithm>
#include <array>
#include <stdexcept>
#include <utility>

namespace {
void check(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
template<class F> void reject(F function) {
    bool rejected = false;
    try { function(); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "invalid settings input accepted");
}
} // namespace

int main() {
    std::vector<std::uint8_t> room(0x3c0 + 19, 0xa5), settings(mco::room_settings_min_size + 17);
    for (std::size_t i = 0; i < settings.size(); ++i) settings[i] = static_cast<std::uint8_t>(i * 71 + 1);
    settings[0] = 'n'; settings[1] = 'e'; settings[2] = 'w'; settings[3] = 0;
    settings[0x30] = 'x'; settings[0x31] = 0;
    const auto original_room = room, original_settings = settings;
    auto expected = room;
    constexpr std::array<std::pair<std::size_t, std::size_t>, 8> ranges{{
        {0,4},{0x54,256},{0x30,2},{0x20,16},{0x40,5},{0x46,8},{0x50,4},{0x154,6}}};
    for (const auto& [offset, size] : ranges)
        std::copy_n(settings.begin() + offset, size, expected.begin() + 0xa0 + offset);
    const auto result = mco::apply_room_settings(room, settings);
    check(result == expected, "known fields, string tails or unrelated bytes mismatch");
    check(room == original_room && settings == original_settings, "source/destination input modified");
    for (std::size_t size : {std::size_t{0}, std::size_t{1}, std::size_t{31}}) {
        std::fill(settings.begin(), settings.begin() + 32, std::uint8_t{'n'});
        settings[size] = 0;
        for (std::size_t secondary : {std::size_t{0}, std::size_t{1}, std::size_t{15}}) {
            std::fill(settings.begin() + 0x30, settings.begin() + 0x40, std::uint8_t{'s'});
            settings[0x30 + secondary] = 0;
            const auto copied = mco::apply_room_settings(room, settings);
            check(std::equal(settings.begin(), settings.begin() + size + 1, copied.begin() + 0xa0), "name terminator missing");
            check(std::equal(settings.begin() + 0x30, settings.begin() + 0x30 + secondary + 1, copied.begin() + 0xd0),
                  "secondary terminator missing");
            for (std::size_t i = size + 1; i < 32; ++i) check(copied[0xa0 + i] == room[0xa0 + i], "name tail overwritten");
            for (std::size_t i = secondary + 1; i < 16; ++i) check(copied[0xd0 + i] == room[0xd0 + i], "secondary tail overwritten");
        }
    }
    reject([&] { mco::apply_room_settings(std::span<const std::uint8_t>{room}.first(0x1f9), settings); });
    reject([&] { mco::apply_room_settings(room, std::span<const std::uint8_t>{settings}.first(0x159)); });
    const std::vector<std::uint8_t> oversized(65537);
    reject([&] { mco::apply_room_settings(oversized, settings); });
    reject([&] { mco::apply_room_settings(room, oversized); });
    for (const auto& [offset, size] : {std::pair<std::size_t,std::size_t>{0,32}, {0x30,16}}) {
        auto corrupt = settings;
        std::fill_n(corrupt.begin() + offset, size, std::uint8_t{'X'});
        reject([&] { mco::apply_room_settings(room, corrupt); });
    }
    const std::vector<std::uint8_t> minimum_room(0x1fa), minimum_settings(0x15a), maximum(65536);
    check(mco::apply_room_settings(minimum_room, minimum_settings).size() == 0x1fa, "minimum sizes rejected");
    check(mco::apply_room_settings(maximum, maximum).size() == 65536, "maximum sizes rejected");
}
