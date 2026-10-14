#include "mco/room_settings.hpp"

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
std::size_t string_size(std::span<const std::uint8_t> settings, std::size_t offset, std::size_t capacity) {
    const auto region = settings.subspan(offset, capacity);
    const auto end = std::find(region.begin(), region.end(), std::uint8_t{0});
    if (end == region.end()) throw std::invalid_argument("settings string requires NUL inside field");
    return static_cast<std::size_t>(end - region.begin()) + 1;
}
} // namespace

std::vector<std::uint8_t> apply_room_settings(std::span<const std::uint8_t> room_image,
                                           std::span<const std::uint8_t> settings_image) {
    validate(room_image, room_settings_offset + room_settings_min_size);
    validate(settings_image, room_settings_min_size);
    const auto name_size = string_size(settings_image, 0, 32);
    const auto secondary_size = string_size(settings_image, 0x30, 16);
    std::vector<std::uint8_t> result(room_image.begin(), room_image.end());
    auto copy = [&](std::size_t offset, std::size_t count) {
        std::copy_n(settings_image.begin() + offset, count, result.begin() + room_settings_offset + offset);
    };
    // Retain original copy order: name, opaque region, secondary string, scalars.
    copy(0, name_size);
    copy(0x54, 256);
    copy(0x30, secondary_size);
    constexpr std::array<std::pair<std::size_t, std::size_t>, 13> fields{{
        {0x24,4},{0x2c,4},{0x20,4},{0x40,2},{0x154,4},{0x42,2},{0x4c,2},
        {0x158,2},{0x46,2},{0x48,4},{0x44,1},{0x28,4},{0x50,4}}};
    for (const auto& [offset, count] : fields) copy(offset, count);
    return result;
}
} // namespace mco
