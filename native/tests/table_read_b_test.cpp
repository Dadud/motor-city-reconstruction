#include "mco/table_read_b.hpp"
#include <array>
#include <stdexcept>
int main() {
    std::array<std::byte, 12> table{};
    for (unsigned k = 0; k < 12; ++k)
        table[k] = static_cast<std::byte>(0xab);
    if (mco::table_read_b(table, 2) != 0xababababu)
        throw std::runtime_error("indexed read regression");
    try { mco::table_read_b(table, 3); }
    catch (const std::invalid_argument&) { return 0; }
    throw std::runtime_error("index past the table must be rejected");
}
