#include "mco/table_slot_clear.hpp"
#include <stdexcept>
int main() {
    std::array<std::byte,7> short_target{};
    std::array<std::span<std::byte>,1> table{short_target};
    try { mco::table_slot_clear(table, 0); }
    catch (const std::invalid_argument&) {
        try { mco::table_slot_clear(table, 1); }
        catch (const std::out_of_range&) { return 0; }
    }
    throw std::runtime_error("invalid table target or slot accepted");
}
