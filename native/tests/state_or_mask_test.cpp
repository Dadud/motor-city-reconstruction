#include "mco/state_or_mask.hpp"
#include <stdexcept>
int main() {
    const std::uint32_t cases[][2] = {{0,0},{0xffffffffu,0u},{0u,0xffffffffu},
        {0x6c00u,0x0130u},{0x80000000u,0x80000000u},{0x12345678u,0xf0f0f0f0u}};
    const std::uint32_t want[] = {0u,0xffffffffu,0xffffffffu,0x6d30u,
        0x80000000u,0xf2f4f6f8u};
    for (unsigned i = 0; i < sizeof cases/sizeof cases[0]; ++i)
        if (mco::state_or_mask(cases[i][0], cases[i][1]) != want[i])
            throw std::runtime_error("or-mask regression");
    return 0;
}
