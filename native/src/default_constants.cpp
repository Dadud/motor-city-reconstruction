#include "mco/default_constants.hpp"
#include <array>

namespace mco {

// Whole body at 0x42cae0: the original writes the raw constants 100.0, 50.0
// and 30.0 into emulated memory, so the host form returns them verbatim.
std::array<std::uint32_t,3> default_constants() {
    return {0x42c80000u, 0x42480000u, 0x41f00000u};
}
}  // namespace mco
