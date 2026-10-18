#include "mco/state_or_mask.hpp"

namespace mco {

// Whole body at 0x414bf0: the 0x6c state word takes the value ORed with the mask.
std::uint32_t state_or_mask(std::uint32_t state, std::uint32_t mask) {
    return state | mask;
}
}  // namespace mco
