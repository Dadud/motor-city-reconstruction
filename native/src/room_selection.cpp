#include "mco/room_selection.hpp"

#include <algorithm>
#include <array>
#include <stdexcept>
#include <utility>

namespace mco {
namespace {
void validate(std::span<const std::uint8_t> image, std::size_t minimum) {
    if (image.size() < minimum || image.size() > 65536)
        throw std::invalid_argument("expected bounded room/settings image");
}
std::uint32_t read(std::span<const std::uint8_t> image, std::size_t offset, std::size_t size) {
    std::uint32_t value = 0;
    for (std::size_t i = 0; i < size; ++i) value |= static_cast<std::uint32_t>(image[offset + i]) << (8 * i);
    return value;
}
} // namespace

std::vector<std::uint8_t> initialize_room_settings(std::span<const std::uint8_t> image) {
    validate(image, room_settings_min_size);
    std::vector<std::uint8_t> result(image.begin(), image.end());
    constexpr std::array<std::pair<std::size_t, std::size_t>, 11> cleared{{
        {0,32},{0x30,16},{0x54,256},{0x20,12},{0x154,4},{0x42,2},
        {0x4c,2},{0x158,2},{0x46,2},{0x48,4},{0x50,4}}};
    for (const auto& [offset, count] : cleared) std::fill_n(result.begin() + offset, count, std::uint8_t{0});
    result[0x2c] = 0x21;
    std::fill_n(result.begin() + 0x2d, 3, std::uint8_t{0});
    result[0x40] = 2; result[0x41] = 0; result[0x44] = 1;
    return result;
}
RoomSelection select_room(std::span<const std::uint8_t> room_image,
                          std::span<const std::uint8_t> name,
                          std::optional<std::span<const std::uint8_t>> cached_settings) {
    validate(room_image, 0x3ac);
    if (name.size() > 31 || std::find(name.begin(), name.end(), std::uint8_t{0}) != name.end())
        throw std::invalid_argument("room name requires at most 31 bytes without NUL");
    const auto current = room_image.subspan(0xa0, 32);
    const auto end = std::find(current.begin(), current.end(), std::uint8_t{0});
    if (end == current.end()) throw std::invalid_argument("current room name requires bounded NUL");
    const bool active = read(room_image, 0xec, 2) != 0 || read(room_image, 0x3a8, 4) != 0;
    if (active) {
        const auto current_size = static_cast<std::size_t>(end - current.begin());
        const bool equal = name.size() == current_size && std::equal(name.begin(), name.end(), current.begin());
        return {{room_image.begin(), room_image.end()}, equal ? 1 : 0, RoomSelectionSource::active};
    }
    std::vector<std::uint8_t> settings;
    auto source = RoomSelectionSource::defaults;
    if (!cached_settings) {
        settings = initialize_room_settings(std::vector<std::uint8_t>(room_settings_min_size));
        std::copy(name.begin(), name.end(), settings.begin());
        settings[name.size()] = 0;
    } else {
        validate(*cached_settings, room_settings_min_size);
        settings.assign(cached_settings->begin(), cached_settings->end());
        source = RoomSelectionSource::cache;
    }
    settings[0x4c] = settings[0x4d] = 0;
    return {apply_room_settings(room_image, settings), 1, source};
}
} // namespace mco
