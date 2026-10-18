#include "mco/counter_increment.hpp"
#include <stdexcept>
int main() {
    if (mco::counter_increment(0) != 1)
        throw std::runtime_error("zero increments to one");
    if (mco::counter_increment(0xffffffff) != 0)
        throw std::runtime_error("the wrap the original preserves");
    return 0;
}
