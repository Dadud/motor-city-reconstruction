#include "mco/entity_or_store.hpp"
#include <array>
#include <stdexcept>
int main() {
    std::array<std::byte, 0x98> image{};
    image.fill(static_cast<std::byte>(0xff));
    mco::entity_or_store(image, 0);
    auto word = [&image](size_t offset) {
        return static_cast<std::uint32_t>(image[offset])
            | static_cast<std::uint32_t>(image[offset+1]) << 8
            | static_cast<std::uint32_t>(image[offset+2]) << 16
            | static_cast<std::uint32_t>(image[offset+3]) << 24; };
    if (word(0x94) != 0xff000000u)
        throw std::runtime_error("the high byte must be forced");
    mco::entity_or_store(image, 0x00420abc);
    if (word(0x94) != 0xff420abcu)
        throw std::runtime_error("the low bytes must keep the value");
    return 0;
}
