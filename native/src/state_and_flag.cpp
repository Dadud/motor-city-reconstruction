#include "mco/state_and_flag.hpp"

namespace mco {

// Whole body at 0x414c10: a member routine that ANDs the mask into the state
// kept at ECX+0x6c and returns one when the conjunction is nonzero. The
// neg/sbb/neg tail is the compiler's idiom for that cast.
std::uint32_t state_and_flag(std::uint32_t state, std::uint32_t mask) {
    return (state & mask) != 0 ? 1 : 0;
}
}  // namespace mco
