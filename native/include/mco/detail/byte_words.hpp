#pragma once
#include <cstddef>
#include <cstdint>
#include <span>
#include <stdexcept>

namespace mco::detail {
inline std::uint32_t read_word(std::span<const std::byte> image, std::size_t offset) {
    if (offset > image.size() || 4 > image.size()-offset)
        throw std::invalid_argument("word outside supplied image");
    std::uint32_t value = 0;
    for (unsigned k = 0; k < 4; ++k)
        value |= std::to_integer<std::uint32_t>(image[offset+k]) << (k*8);
    return value;
}
inline void write_word(std::span<std::byte> image, std::size_t offset,
                        std::uint32_t value) {
    if (offset > image.size() || 4 > image.size()-offset)
        throw std::invalid_argument("word outside supplied image");
    for (unsigned k = 0; k < 4; ++k)
        image[offset+k] = static_cast<std::byte>((value >> (k*8)) & 255u);
}
}  // namespace mco::detail
