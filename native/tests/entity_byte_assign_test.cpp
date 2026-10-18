#include "mco/entity_byte_assign.hpp"
#include <stdexcept>
int main() {
    mco::entity_byte_assign({}, -1, 0, 1, 0xffffffffu);
    std::array<std::byte,28> table{};
    try { mco::entity_byte_assign(table, 0, 0, 0, 0); }
    catch (const std::invalid_argument&) { return 0; }
    throw std::runtime_error("non-null zero-divisor table accepted");
}
