#include "mco/singleton_quotient.hpp"
#include <limits>
#include <stdexcept>
#include <utility>

int main() {
    if (mco::singleton_quotient(100, 3, 7) != 33)
        throw std::runtime_error("primary global must be the divisor");
    if (mco::singleton_quotient(100, 0, 7) != 14)
        throw std::runtime_error("fallback applies when primary is zero");
    if (mco::singleton_quotient(-100, 7, 3) != -14)
        throw std::runtime_error("IDIV truncates toward zero");
    if (mco::singleton_quotient(100, 0xfffffffb, 3) != -20)
        throw std::runtime_error("the divisor is read signed");
    for (auto [dividend, divisor] : {std::pair{1u, 0u}, {0x80000000u, 0xffffffffu}}) {
        bool rejected = false;
        try {
            mco::singleton_quotient(static_cast<std::int32_t>(dividend), 0u, divisor);
        } catch (const std::invalid_argument&) { rejected = true; }
        if (!rejected)
            throw std::runtime_error("unsupported domain must be rejected");
    }
    return 0;
}
