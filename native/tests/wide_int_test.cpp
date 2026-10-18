#include "mco/detail/wide_int.hpp"
#include <stdexcept>

int main() {
    using mco::detail::wide_int;
    constexpr auto carry = wide_int::from_words({0xffffffffu,0xffffffffu,0,0})+1;
    static_assert(carry.words() == std::array<std::uint32_t,4>{0,0,1,0});
    static_assert((wide_int(-1)>>64) == wide_int(-1));
    static_assert((wide_int(1)<<127) == wide_int::from_words({0,0,0,0x80000000u}));
    static_assert((wide_int(1)<<128) == wide_int(0));
    // 2^53+1 ties down; 2^53+3 ties up to the even significand.
    if (static_cast<double>((wide_int(1)<<53)+1) != 9007199254740992.0
        || static_cast<double>((wide_int(1)<<53)+3) != 9007199254740996.0)
        throw std::runtime_error("wide integer binary64 rounding changed");
}
