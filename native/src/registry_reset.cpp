#include "mco/registry_reset.hpp"

namespace mco {

// Whole body at 0x407550: walk 24-byte records while the cursor stays under
// 0x8e533c, zeroing the first dword, stamping 0xffffffff as the second and
// zeroing the third. Bytes 12..23 of each record are never written.
void registry_reset(std::span<std::byte> registry) {
    constexpr std::size_t stride = 24;
    for (std::size_t offset = 0; offset+12 <= registry.size();
            offset += stride) {
        for (unsigned k = 0; k < 4; ++k) {
            registry[offset+k] = std::byte{0};
            registry[offset+8+k] = std::byte{0};
            registry[offset+4+k] = std::byte{0xff};
        }
    }
}
}  // namespace mco
