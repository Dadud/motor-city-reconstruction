#include "mco/struct_initializer.hpp"

namespace mco {

// Whole body at 0x403200: the count image takes 0x1e and the state image
// takes the raw constants 0x42a00000 followed by two zero dwords.
void struct_initializer(std::span<std::byte,4> count_image,
                       std::span<std::byte,12> state_image) {
    for (unsigned k = 0; k < 4; ++k) {
        count_image[k] = static_cast<std::byte>((0x1e >> (k*8)) & 255);
        state_image[k] = static_cast<std::byte>((0x42a00000u >> (k*8)) & 255);
        state_image[4+k] = std::byte{0};
        state_image[8+k] = std::byte{0};
    }
}
}  // namespace mco
