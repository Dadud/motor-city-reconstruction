#include "mco/buffer_set_length.hpp"
#include <stdexcept>
int main() {
    std::uint32_t length = 17;
    try { mco::buffer_set_length({}, 0, length); }
    catch (const std::out_of_range&) {
        if (length == 17) return 0;
    }
    throw std::runtime_error("invalid buffer changed the length or was accepted");
}
