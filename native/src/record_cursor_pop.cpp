#include "mco/record_cursor_pop.hpp"
#include <stdexcept>
#include "mco/layouts.hpp"

namespace mco {
std::uint32_t record_cursor_pop(std::uint32_t cursor, std::uint32_t base) {
    if (cursor == 0) return base;
    const auto previous = cursor-static_cast<std::uint32_t>(state_record::size);
    return previous < base ? base : previous;
}
}
