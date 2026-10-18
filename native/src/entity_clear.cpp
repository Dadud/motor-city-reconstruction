#include "mco/entity_clear.hpp"
#include <stdexcept>

namespace mco {

// Whole body at 0x408ea0: zero byte 0 and the dwords at 0x104, 0x114, 0x11c
// and 0x118, in the original's order.
void entity_clear(std::span<std::byte> image) {
    if (image.size() < 0x120)
        throw std::invalid_argument("entity image truncated");
    image[0] = std::byte{0};
    for (unsigned k = 0; k < 4; ++k) {
        image[0x104+k] = std::byte{0};
        image[0x114+k] = std::byte{0};
        image[0x11c+k] = std::byte{0};
        image[0x118+k] = std::byte{0};
    }
}
}  // namespace mco
