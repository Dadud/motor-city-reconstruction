#include "mco/clamped_bit_mask.hpp"
#include <stdexcept>
int main() {
    if (mco::clamped_bit_mask(0x7fffffff) != 0x8000u
        || mco::clamped_bit_mask(15) != 1u)
        throw std::runtime_error("mask overflow or clamp changed");
}
