#include "mco/entity_mode_flag.hpp"
#include <stdexcept>
int main() {
    if (mco::entity_mode_flag({}, 0xffffffffu, 0) != 0)
        throw std::runtime_error("null table must return zero");
}
