#include "mco/sentinel_match.hpp"
#include <stdexcept>
int main() {
    if (mco::sentinel_match(0xfeeeeb19) != 1)
        throw std::runtime_error("the sentinel must match");
    if (mco::sentinel_match(0) != 0 || mco::sentinel_match(1) != 0)
        throw std::runtime_error("non-sentinel values must not match");
    return 0;
}
