#include "mco/record_related_value.hpp"
#include <stdexcept>
int main() {
    try { mco::record_related_value({}); }
    catch (const std::invalid_argument&) { return 0; }
    throw std::runtime_error("truncated record accepted");
}
