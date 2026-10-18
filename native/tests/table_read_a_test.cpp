#include "mco/table_read_a.hpp"
#include <array>
#include <stdexcept>
int main() {
    std::array<std::byte, 8> table{};
    for (unsigned k = 0; k < 8; ++k)
        table[k] = static_cast<std::byte>(k*16 + 1);
    if (mco::table_read_a(table, 0) != 0x31211101u)
        throw std::runtime_error("little-endian dword read regression");
    if (mco::table_read_a(table, 1) != 0x71615141u)
        throw std::runtime_error("indexed read regression");
    try { mco::table_read_a(table, 2); }
    catch (const std::invalid_argument&) { return 0; }
    throw std::runtime_error("index past the table must be rejected");
}
