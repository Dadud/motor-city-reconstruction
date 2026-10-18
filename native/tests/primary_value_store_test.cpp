#include "mco/primary_value_store.hpp"
#include <stdexcept>
int main() {
    std::uint32_t destination = 1;
    mco::primary_value_store(destination, 0xffffffffu);
    if (destination != 0xffffffffu) throw std::runtime_error("global assignment changed bits");
}
