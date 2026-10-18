#include "mco/record_identifier.hpp"
#include <stdexcept>
int main() {
    try { mco::record_identifier({}); }
    catch (const std::invalid_argument&) { return 0; }
    throw std::runtime_error("truncated record accepted");
}
