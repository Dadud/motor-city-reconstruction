#include "mco/record_flag_toggle.hpp"
#include <stdexcept>
int main() {
    try { mco::record_flag_toggle({}); }
    catch (const std::invalid_argument&) { return 0; }
    throw std::runtime_error("truncated record accepted");
}
