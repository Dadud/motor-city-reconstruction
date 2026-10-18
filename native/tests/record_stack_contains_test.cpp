#include "mco/record_stack_contains.hpp"
#include <stdexcept>
int main() {
    std::array<std::byte,8> record{};
    record[4] = std::byte{7};
    if (mco::record_stack_contains(record, 0x1000, 0, 7) != 1
        || mco::record_stack_contains(record, 0x1000, 0, 8) != 0)
        throw std::runtime_error("base record must be checked with a null cursor");
}
