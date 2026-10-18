#include "mco/copy_line_segment.hpp"
#include <stdexcept>
int main() {
    std::array<std::byte,4> destination{};
    std::array<std::byte,2> source{std::byte{'A'},std::byte{10}};
    if (mco::copy_line_segment(destination, source, 0) != 2
        || destination[0] != std::byte{'A'} || destination[1] != std::byte{0}
        || mco::copy_line_segment(destination, {}, -1) != 1 || destination[0] != std::byte{0})
        throw std::runtime_error("inclusive limit or mandatory source skip changed");
}
