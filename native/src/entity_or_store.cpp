#include "mco/entity_or_store.hpp"
#include <stdexcept>

namespace mco {

// Whole body at 0x409110: image[0x94] = value | 0xff000000.
void entity_or_store(std::span<std::byte> image, std::uint32_t value) {
    if (image.size() < 0x98)
        throw std::invalid_argument("entity image truncated");
    const std::uint32_t combined = value | 0xff000000u;
    for (unsigned k = 0; k < 4; ++k)
        image[0x94+k] = static_cast<std::byte>((combined >> (k*8)) & 255);
}
}  // namespace mco
