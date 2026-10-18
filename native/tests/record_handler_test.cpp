#include "mco/record_handler.hpp"
#include <stdexcept>
int main() {
    if (mco::record_handler(24) != 0x432180 || mco::record_handler(0xffffffffu) != 0x433200)
        throw std::runtime_error("callback selection changed");
}
