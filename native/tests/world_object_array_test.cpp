#include "mco/world_object_array.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <stdexcept>
#include <vector>

int main() {
    std::vector<std::uint32_t> calls;
    mco::update_active_world_objects(0x1000,{true,false,true},
        [&](auto address){calls.push_back(address);});
    assert((calls==std::vector<std::uint32_t>{0x1000,0x19f0}));
    bool rejected=false;
    try { mco::update_active_world_objects(0x1000,{},{}); }
    catch(const std::invalid_argument&) { rejected=true; }
    assert(rejected);
    rejected=false;
    try { mco::update_active_world_objects(0,{},[](auto){}); }
    catch(const std::invalid_argument&) { rejected=true; }
    assert(rejected);
}
