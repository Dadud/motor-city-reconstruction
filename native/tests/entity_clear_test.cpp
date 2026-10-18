#include "mco/entity_clear.hpp"
#include <array>
#include <stdexcept>
int main() {
    std::array<std::byte, 0x120> image{};
    image.fill(static_cast<std::byte>(0xff));
    mco::entity_clear(image);
    if (image[0] != std::byte{0})
        throw std::runtime_error("byte 0 must clear");
    for (unsigned offset : {0x104u, 0x114u, 0x118u, 0x11cu})
        for (unsigned k = 0; k < 4; ++k)
            if (image[offset+k] != std::byte{0})
                throw std::runtime_error("field must clear");
    if (image[0x108] != std::byte{0xff})
        throw std::runtime_error("bytes between fields must stay");
    return 0;
}
