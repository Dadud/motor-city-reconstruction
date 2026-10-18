#include "mco/record_cursor_pop.hpp"
#include <stdexcept>
int main() {
    if (mco::record_cursor_pop(1, 0) != 0xffffff01u
        || mco::record_cursor_pop(0, 0x1234u) != 0x1234u)
        throw std::runtime_error("unsigned cursor clamp changed");
}
