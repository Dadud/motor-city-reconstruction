#include "mco/default_constants.hpp"
#include <stdexcept>
int main() {
    const auto values = mco::default_constants();
    if (values[0] != 0x42c80000u || values[1] != 0x42480000u
            || values[2] != 0x41f00000u)
        throw std::runtime_error("default constants regression");
    return 0;
}
