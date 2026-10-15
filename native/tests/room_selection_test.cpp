#include "mco/room_selection.hpp"

#include <algorithm>
#include <array>
#include <stdexcept>

namespace {
void check(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
void put(std::vector<std::uint8_t>& bytes, std::size_t offset, std::uint32_t value, std::size_t size = 4) {
    for (std::size_t i = 0; i < size; ++i) bytes[offset + i] = static_cast<std::uint8_t>(value >> (8 * i));
}
std::vector<std::uint8_t> room() {
    std::vector<std::uint8_t> bytes(0x3c0, 0xa5);
    bytes[0xa0] = 'o'; bytes[0xa1] = 'l'; bytes[0xa2] = 'd'; bytes[0xa3] = 0;
    put(bytes, 0xec, 0, 2); put(bytes, 0x3a8, 0); put(bytes, 0x39c, 7);
    return bytes;
}
template<class F> void reject(F function) {
    bool rejected = false;
    try { function(); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "invalid room selection input accepted");
}
} // namespace

int main() {
    const auto initialized = mco::initialize_room_settings(std::vector<std::uint8_t>(0x160, 0xa5));
    check(initialized[0x45] == 0xa5 && initialized[0x4e] == 0xa5 && initialized[0x4f] == 0xa5,
          "initializer changed unspecified padding");
    check(initialized[0x2c] == 0x21 && initialized[0x2d] == 0 && initialized[0x40] == 2 && initialized[0x44] == 1,
          "initializer default values mismatch");
    for (std::size_t i = 0x15a; i < initialized.size(); ++i) check(initialized[i] == 0xa5, "initializer changed image tail");
    const std::array<std::uint8_t, 3> name{'n','e','w'};
    const auto original = room();
    const auto selected = mco::select_room(original, name);
    auto expected_settings = mco::initialize_room_settings(std::vector<std::uint8_t>(0x15a));
    std::copy(name.begin(), name.end(), expected_settings.begin());
    check(selected.result == 1 && selected.source == mco::RoomSelectionSource::defaults &&
          selected.room_image == mco::apply_room_settings(original, expected_settings), "default selection mismatch");
    check(selected.room_image[0x39c] == 7, "default selection changed server selector");
    auto cached = mco::initialize_room_settings(std::vector<std::uint8_t>(0x160, 0x5a));
    cached[0] = 'c'; cached[1] = 0;
    put(cached, 0x20, 123); put(cached, 0x4c, 99, 2); put(cached, 0x46, 77, 2);
    const auto cache_before = cached;
    const auto hit = mco::select_room(original, name, std::span<const std::uint8_t>{cached});
    auto cleared_cache = cached; put(cleared_cache, 0x4c, 0, 2);
    check(hit.source == mco::RoomSelectionSource::cache && hit.result == 1 &&
          hit.room_image == mco::apply_room_settings(original, cleared_cache), "cache hit or forced disconnected field mismatch");
    check(hit.room_image[0xec] == 0 && hit.room_image[0xed] == 0 && hit.room_image[0xe6] == 77,
          "cache selection must clear connected while preserving maxReady");
    check(cached == cache_before, "cached settings modified");
    const std::vector<std::uint8_t> invalid_cache{1};
    for (auto offset : {0xec, 0x3a8}) {
        auto active = original; put(active, offset, 1, offset == 0xec ? 2 : 4);
        for (const auto& requested : {std::array<std::uint8_t,3>{'o','l','d'}, {'O','L','D'}, {'n','e','w'}}) {
            const auto reused = mco::select_room(active, requested, std::span<const std::uint8_t>{invalid_cache});
            check(reused.source == mco::RoomSelectionSource::active && reused.room_image == active,
                  "active selection consulted cache or modified image");
            check(reused.result == (requested[0] == 'o' ? 1 : 0), "active comparison was not exact-case");
        }
    }
    const std::array<std::uint8_t,3> nul_name{'a',0,'b'};
    reject([&] { mco::select_room(original, nul_name); });
    reject([&] { mco::select_room(original, std::vector<std::uint8_t>(32, 'x')); });
    reject([&] { mco::select_room(original, name, std::span<const std::uint8_t>{invalid_cache}); });
    auto unterminated = original;
    std::fill_n(unterminated.begin() + 0xa0, 32, std::uint8_t{'x'});
    reject([&] { mco::select_room(unterminated, name); });
    reject([] { mco::initialize_room_settings(std::vector<std::uint8_t>(0x159)); });
    reject([] { mco::initialize_room_settings(std::vector<std::uint8_t>(65537)); });
    reject([&] { mco::select_room(std::vector<std::uint8_t>(0x3ab), name); });
    check(mco::select_room(original, std::span<const std::uint8_t>{}).room_image[0xa0] == 0, "empty default name rejected");
    check(room() == original, "input image changed");
}
