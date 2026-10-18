#include "mco/scratch_clear_return.hpp"

#include <stdexcept>

namespace mco {

// Whole body at 0x4082c0: the primary global is read first, the fallback
// target is cleared when present, and the primary is returned. An empty span
// represents a null fallback, preserving the original's conditional store.
std::uint32_t clear_through(std::span<std::byte> fallback_target,
                            std::uint32_t primary) {
    if (fallback_target.empty()) return primary;
    if (fallback_target.size() < 4) throw std::invalid_argument("fallback target truncated");
    for (unsigned k = 0; k < 4; ++k)
        fallback_target[k] = std::byte{0};
    return primary;
}
}  // namespace mco
