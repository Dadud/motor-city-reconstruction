#include "mco/lobby_channel_record.hpp"

#include <algorithm>
#include <stdexcept>
#include <utility>

namespace mco {
namespace {
void put(ChannelImage& image, std::size_t offset, std::size_t width,
         std::uint32_t value) {
    for (std::size_t index = 0; index < width; ++index)
        image[offset + index] = static_cast<std::uint8_t>(value >> (8 * index));
}
struct Copy { std::size_t source, target, width; };
} // namespace

ChannelImage initialize_channel_image(std::span<const std::uint8_t> argument,
                                      std::span<const std::uint8_t> allocated_image) {
    if (argument.size() != channel_argument_size || allocated_image.size() != channel_allocation_size)
        throw std::invalid_argument("expected exact argument and explicit channel allocation image");
    ChannelImage image;
    std::copy(allocated_image.begin(), allocated_image.end(), image.begin());
    for (const auto [start, end] : {std::pair{0x38,0x58}, std::pair{0x70,0x81}, std::pair{0x90,0x190}})
        std::fill(image.begin() + start, image.begin() + end, 0);
    for (auto offset : {8,0x2c,0x30,0x58,0x60,0x88,0x190,0x194,0x19c}) put(image,offset,4,0);
    for (auto offset : {0x64,0x66,0x6a,0x6c,0x82,0x86,0x198}) put(image,offset,2,0);
    put(image,0x34,4,0xffffffff);
    put(image,0x68,2,1);
    put(image,0x84,1,1);
    std::uint32_t flags = 0;
    for (std::size_t index = 0; index < 4; ++index)
        flags |= static_cast<std::uint32_t>(argument[0xc + index]) << (8 * index);
    put(image,0x6e,2,(flags & 1) ? 1 : ((flags & 4) ? 4 : 2));
    put(image,0x6a,2,flags & 0x20);
    put(image,0x82,2,flags & 0x4000);
    constexpr Copy copies[]{{0,4,4},{4,0x5c,4},{8,8,4},{0xc,0x190,4},
        {0x34,0x70,17},{0x48,0x88,4},{0x4c,0x8c,4},{0x50,0x90,256},{0x150,0x86,2}};
    for (const auto& copy : copies)
        std::copy_n(argument.begin() + copy.source, copy.width, image.begin() + copy.target);
    // Original strncpy(...,30) pads through byte 29 after a NUL. Bytes 30/31
    // of the surrounding name region are allocation contents, not defaults.
    bool nul = false;
    for (std::size_t index = 0; index < 30; ++index) {
        if (argument[0x10 + index] == 0) nul = true;
        image[0xc + index] = nul ? 0 : argument[0x10 + index];
    }
    return image;
}

ChannelRecord materialize_channel_record(std::span<const std::uint8_t> channel_image) {
    if (channel_image.size() != channel_allocation_size)
        throw std::invalid_argument("expected complete channel image");
    ChannelRecord record;
    std::copy_n(channel_image.begin() + 0x1a0, channel_record_size, record.begin());
    constexpr Copy copies[]{
        {8,0x1a0,4},{0x2c,0x1c4,4},{0x30,0x1c8,4},{0x34,0x1cc,4},
        {0x58,0x1f0,4},{0x5c,0x1f4,4},{0x60,0x1f8,4},{0x64,0x1fc,2},
        {0x66,0x1fe,2},{0x68,0x200,2},{0x6a,0x202,2},{0x6c,0x204,2},
        {0x6e,0x206,2},{0x82,0x226,2},{0x84,0x228,1},{0x86,0x22c,2},
        {0x88,0x230,4},{0x8c,0x234,4},{0x190,0x340,4},{0xc,0x1a4,32},
        {0x38,0x1d0,16},{0x48,0x1e0,16},{0x90,0x240,256},{0x70,0x214,17}};
    for (const auto& copy : copies)
        std::copy_n(channel_image.begin() + copy.source, copy.width,
                    record.begin() + copy.target - 0x1a0);
    // The original also writes a short at 0x346, beyond the wire record.
    // This API returns the wire record only and does not expose that metadata.
    return record;
}

} // namespace mco
