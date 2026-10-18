#include "mco/indexed_masked_bit.hpp"
#include <stdexcept>
int main() {
    try { mco::indexed_masked_bit({}, 0xffffffffu, 0); }
    catch (const std::invalid_argument&) { return 0; }
    throw std::runtime_error("missing record accepted");
}
