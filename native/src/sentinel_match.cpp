#include "mco/sentinel_match.hpp"

namespace mco {

// Whole body at 0x428980: sete on the comparison, so the result is exactly
// the equality against the 0xfeeeeb19 constant.
std::uint32_t sentinel_match(std::uint32_t value) {
    return value == 0xfeeeeb19u ? 1 : 0;
}
}  // namespace mco
