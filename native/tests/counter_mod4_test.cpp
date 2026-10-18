#include "mco/counter_mod4.hpp"
#include <stdexcept>
int main() {
    // The expected column is the original's own output, read from the oracle
    // at tools/w0_pseudocode_oracle, including the negative-branch values.
    const std::uint32_t in[] = {0u,1u,2u,3u,4u,5u,0xffffffffu,0xfffffffeu,
        0x7fffffffu,0x80000000u};
    const std::uint32_t want[] = {1u,2u,3u,0u,1u,2u,0u,0xffffffffu,0u,
        0xfffffffdu};
    for (unsigned i = 0; i < sizeof in/sizeof in[0]; ++i)
        if (mco::counter_mod4(in[i]) != want[i])
            throw std::runtime_error("mod4 counter regression");
    return 0;
}
