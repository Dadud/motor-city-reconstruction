#include "mco/registry_slot_used.hpp"
#include <cstddef>
#include <stdexcept>

namespace mco {

// Whole body at 0x407d70: setne on dword[slot*24] of the registry table.
std::uint32_t registry_slot_used(const std::span<const std::byte> registry,
                                 std::uint32_t slot) {
    const std::size_t base = static_cast<std::size_t>(slot)*24;
    if (base+4 > registry.size())
        throw std::invalid_argument("registry slot outside the table");
    const unsigned combined = std::to_integer<unsigned>(registry[base])
        | std::to_integer<unsigned>(registry[base+1])
        | std::to_integer<unsigned>(registry[base+2])
        | std::to_integer<unsigned>(registry[base+3]);
    return combined != 0 ? 1u : 0u;
}
}  // namespace mco
