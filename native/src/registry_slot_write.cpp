#include "mco/registry_slot_write.hpp"
#include <stdexcept>

namespace mco {

// Whole body at 0x4077a0: slot stride is 24 bytes and the three arguments
// land at offsets 12, 16 and 20 of the slot.
void registry_slot_write(std::span<std::byte> registry, std::uint32_t slot,
                         std::uint32_t first, std::uint32_t second,
                         std::uint32_t third) {
    const std::uint32_t values[3] = {first, second, third};
    const std::size_t base = static_cast<std::size_t>(slot)*24 + 12;
    if (base+12 > registry.size())
        throw std::invalid_argument("registry slot outside the table");
    for (unsigned which = 0; which < 3; ++which)
        for (unsigned k = 0; k < 4; ++k)
            registry[base+which*4+k] = static_cast<std::byte>(
                (values[which] >> (k*8)) & 255);
}
}  // namespace mco
