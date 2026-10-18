#include "mco/cyclic_index_difference.hpp"
#include <stdexcept>
int main() {
    if (mco::cyclic_index_difference(11, 0, 12, 0) != -1
        || mco::cyclic_index_difference(0, 11, 12, 0) != 1
        || mco::cyclic_index_difference(11, 0, 12, 1) != 11)
        throw std::runtime_error("cyclic difference branches changed");
}
