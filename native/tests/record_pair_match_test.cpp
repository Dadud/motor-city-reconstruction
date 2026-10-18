#include "mco/record_pair_match.hpp"
#include <stdexcept>
int main() {
    std::array<std::byte,4> pairs{};
    pairs.fill(std::byte{0xff});
    if (mco::record_pair_match(pairs, 0xffffffffu, 0) != 0)
        throw std::runtime_error("sentinel must precede second-word access");
}
