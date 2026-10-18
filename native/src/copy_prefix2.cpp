#include "mco/copy_prefix2.hpp"
#include <stdexcept>

namespace mco {
void copy_prefix2(std::span<std::byte,3> destination,
                  std::span<const std::byte,2> source) {
    const auto second = source[1];
    destination[0] = source[0];
    destination[1] = second;
    destination[2] = std::byte{0};
}
}
