#include "mco/zero_flag.hpp"

namespace mco {

// Whole body at 0x423310: the value arrives in the global at 0x929888 and the
// predicate is stored back into the same global, so the host form is the pure
// computation.
std::uint32_t zero_flag(std::uint32_t value) {
    return value == 0 ? 1 : 0;
}
}  // namespace mco
