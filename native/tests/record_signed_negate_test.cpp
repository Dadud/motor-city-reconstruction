#include "mco/record_signed_negate.hpp"
#include <stdexcept>
int main() {
    try { mco::record_signed_negate({}); }
    catch (const std::invalid_argument&) { return 0; }
    throw std::runtime_error("truncated record accepted");
}
