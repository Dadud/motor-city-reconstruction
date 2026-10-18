#include "mco/cyclic_index_difference.hpp"
#include <bit>
#include <stdexcept>

namespace mco {
std::int32_t cyclic_index_difference(std::int32_t first, std::int32_t second,
                                      std::int32_t count, std::uint32_t mode) {
    const auto bits = std::bit_cast<std::uint32_t>(first)-std::bit_cast<std::uint32_t>(second);
    const auto difference = std::bit_cast<std::int32_t>(bits);
    if (mode != 0) return difference;
    const auto half = count >> 1;
    if (difference > half)
        return std::bit_cast<std::int32_t>(bits-std::bit_cast<std::uint32_t>(count));
    if (difference < -half)
        return std::bit_cast<std::int32_t>(bits+std::bit_cast<std::uint32_t>(count));
    return difference;
}
}
