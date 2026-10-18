#include "mco/zero_flag.hpp"
#include <stdexcept>
int main() {
    if (mco::zero_flag(0) != 1)
        throw std::runtime_error("zero must read as one");
    if (mco::zero_flag(5) != 0 || mco::zero_flag(0xffffffff) != 0)
        throw std::runtime_error("nonzero must read as zero");
    return 0;
}
