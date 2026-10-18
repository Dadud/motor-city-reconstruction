#include "mco/counter_increment.hpp"

namespace mco {

// Whole body at 0x41bf80: increment the counter, whose wrap the original
// also preserves.
std::uint32_t counter_increment(std::uint32_t counter) {
    return counter+1;
}
}  // namespace mco
