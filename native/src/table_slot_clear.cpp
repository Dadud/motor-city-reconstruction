#include "mco/table_slot_clear.hpp"
#include <stdexcept>
namespace mco {
void table_slot_clear(std::span<const std::span<std::byte>> table,
                      std::uint32_t slot) {
    if (slot >= table.size())
        throw std::out_of_range("slot outside pointer table");
    auto target = table[slot];
    if (target.empty()) return;
    if (target.size() < 8)
        throw std::invalid_argument("table target truncated");
    for (unsigned k = 4; k < 8; ++k) target[k] = std::byte{0};
}
}
