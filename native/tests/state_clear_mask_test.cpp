#include "mco/state_clear_mask.hpp"
#include <stdexcept>
int main() {
    if (mco::state_clear_mask(0xff, 0x0f) != 0xf0)
        throw std::runtime_error("masked bits must clear");
    if (mco::state_clear_mask(0xff, 0) != 0xff)
        throw std::runtime_error("empty mask must keep the state");
    if (mco::state_clear_mask(0xff, 0xffffffff) != 0)
        throw std::runtime_error("full mask must clear the state");
    return 0;
}
