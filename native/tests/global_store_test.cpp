#include "mco/global_store.hpp"
#include <array>
#include <stdexcept>

int main() {
    std::array<std::byte,4> image{};
    if (mco::global_store(image, 0x1234, 0x4321) != 0x4321)
        throw std::runtime_error("global store must return the third global");
    const auto stored = static_cast<std::uint32_t>(image[0])
        | static_cast<std::uint32_t>(image[1]) << 8
        | static_cast<std::uint32_t>(image[2]) << 16
        | static_cast<std::uint32_t>(image[3]) << 24;
    if (stored != 0x1234)
        throw std::runtime_error("global store must write little-endian");
    if (mco::global_store(image, 0, 0) != 0)
        throw std::runtime_error("zero store must return zero");
    const auto zeroed = static_cast<std::uint32_t>(image[0])
        | static_cast<std::uint32_t>(image[1]) << 8
        | static_cast<std::uint32_t>(image[2]) << 16
        | static_cast<std::uint32_t>(image[3]) << 24;
    if (zeroed != 0)
        throw std::runtime_error("zero store must clear the image");
    return 0;
}
