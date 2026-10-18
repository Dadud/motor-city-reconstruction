#include "mco/instance_accessor.hpp"

namespace mco {

// Whole body at 0x405900: read the primary global, return it when nonzero,
// otherwise return the fallback global. Comparison is on the loaded value, so
// any nonzero primary wins regardless of how it was produced.
std::uint32_t instance_accessor(std::uint32_t primary, std::uint32_t fallback) {
    return primary != 0 ? primary : fallback;
}
}  // namespace mco