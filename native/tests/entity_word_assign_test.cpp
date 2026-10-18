#include "mco/entity_word_assign.hpp"
#include <stdexcept>
int main() {
    mco::entity_word_assign({}, -1, 0, 1, 0xffffffffu);
    std::array<std::byte,28> table{};
    bool zero_count = false, nan = false;
    try { mco::entity_word_assign(table, 0, 0, 0, 0); }
    catch (const std::invalid_argument&) { zero_count = true; }
    try { mco::entity_word_assign(table, 0, 1, 0, 0x7f800001u); }
    catch (const std::invalid_argument&) { nan = true; }
    if (!zero_count || !nan)
        throw std::runtime_error("unverified divisor or NaN input accepted");
}
