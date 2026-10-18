#include "mco/state_clear_mask.hpp"

namespace mco {

// Whole body at 0x414c30: clear the masked bits of the state kept at
// ECX+0x6c, which is what the original stores back. The member value is the
// return, matching the original's use of EDX.
std::uint32_t state_clear_mask(std::uint32_t state, std::uint32_t mask) {
    return state & ~mask;
}
}  // namespace mco
