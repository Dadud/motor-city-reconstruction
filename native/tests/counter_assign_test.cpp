#include "mco/counter_assign.hpp"
#include <stdexcept>
int main() {
    std::uint32_t destination = 1;
    mco::counter_assign(destination, 0xffffffffu);
    if (destination != 0xffffffffu) throw std::runtime_error("global assignment changed bits");
}
