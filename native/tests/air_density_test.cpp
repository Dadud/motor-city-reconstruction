#include "mco/air_density.hpp"
#undef NDEBUG
#include <cassert>
int main() {
    const auto base=mco::calculate_air_density(0,false,false,0);
    assert(mco::calculate_air_density(0,true,false,0)>base);
    assert(mco::calculate_air_density(0,false,true,2)>base);
    assert(mco::calculate_air_density(0,false,false,2)==base);
}
