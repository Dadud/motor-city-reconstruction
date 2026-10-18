#include "mco/singleton_quotient.hpp"
#include <limits>
#include <stdexcept>

namespace mco {

// Whole body at 0x405910: divide the dividend by the primary global when it
// is nonzero, otherwise by the fallback, exactly as IDIV does - signed and
// truncating toward zero. A zero divisor faults in the original and the
// INT_MIN/-1 pair overflows, so both are rejected as outside the supported
// domain rather than emulated.
std::int32_t singleton_quotient(std::int32_t dividend, std::uint32_t primary,
                                std::uint32_t fallback) {
    const std::uint32_t chosen = primary != 0 ? primary : fallback;
    const std::int32_t divisor = static_cast<std::int32_t>(chosen);
    if (divisor == 0 || (dividend == std::numeric_limits<std::int32_t>::min()
                         && divisor == -1))
        throw std::invalid_argument(
            "singleton quotient divisor outside the supported domain");
    return static_cast<std::int32_t>(dividend/divisor);
}
}  // namespace mco
