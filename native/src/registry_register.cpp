#include "mco/registry_register.hpp"

namespace mco {

// Whole body at 0x4072c0: stamp the node with the current counter, link it to
// the current head, and hand back the incremented counter. The caller then
// records the node as the new head, because the node address is an emulated
// value the host never dereferences.
std::uint32_t registry_register(std::span<std::byte,0x58> node,
                                std::uint32_t counter, std::uint32_t head) {
    for (unsigned k = 0; k < 4; ++k) {
        node[0x20+k] = static_cast<std::byte>((counter >> (k*8)) & 255);
        node[0x54+k] = static_cast<std::byte>((head >> (k*8)) & 255);
    }
    return counter+1;
}
}  // namespace mco
