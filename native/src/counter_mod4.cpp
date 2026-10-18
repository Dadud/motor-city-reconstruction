#include "mco/counter_mod4.hpp"

namespace mco {

// Whole body at 0x42cc60: mask the increment with 0x80000003, then repair a
// negative result the way the original's signed fixup does.
std::uint32_t counter_mod4(std::uint32_t counter) {
    std::uint32_t stepped = (counter + 1u) & 0x80000003u;
    if (static_cast<std::int32_t>(stepped) < 0)
        stepped = (stepped - 1u | 0xfffffffcu) + 1u;
    return stepped;
}
}  // namespace mco
