#include "mco/clamped_bit_mask.hpp"
#include <bit>
#include <stdexcept>

namespace mco {
std::uint32_t clamped_bit_mask(std::int32_t index) {
    auto stepped = std::bit_cast<std::int32_t>(std::bit_cast<std::uint32_t>(index)+1u);
    if (stepped < 0) stepped = 0;
    if (stepped > 15) stepped = 15;
    return 1u << (15-static_cast<unsigned>(stepped));
}
}
