#include "mco/state_and_flag.hpp"
#include <stdexcept>
int main() {
    if (mco::state_and_flag(0xf0, 0x0f) != 0)
        throw std::runtime_error("disjoint bits must yield zero");
    if (mco::state_and_flag(0xf0, 0x10) != 1)
        throw std::runtime_error("shared bits must yield one");
    if (mco::state_and_flag(0xffffffff, 0xffffffff) != 1)
        throw std::runtime_error("all bits regression");
    return 0;
}
