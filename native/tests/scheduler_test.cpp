#include "mco/scheduler.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <stdexcept>

int main() {
    std::vector<mco::ScheduledCall> entries;
    for(auto entry : {mco::ScheduledCall{30,1,10}, {-1,2,20}, {30,3,30}, {6,4,40}})
        mco::insert_callback(entries,entry);
    assert(entries[0].callback==2 && entries[1].callback==4 && entries[2].callback==1 && entries[3].callback==3);
    entries={{6,1,10},{30,2,20}};
    std::vector<std::uint32_t> calls;
    mco::execute_callbacks(entries,[&](auto callback,auto payload) {
        calls.push_back(callback); calls.push_back(payload);
        if(calls.size()==2) { entries[1]={30,3,30};entries.push_back({40,4,40}); }
    });
    assert((calls==std::vector<std::uint32_t>{1,10,3,30}));
    calls.clear();
    auto result=mco::execute_batch(0xffffffffu,2,false,[&]{calls.push_back(1);},
        [&]{calls.push_back(2);},[&]{calls.push_back(3);});
    assert(result==1 && (calls==std::vector<std::uint32_t>{2,3,1,2,3}));
    assert(mco::selected_iterations(true,0,-4)==1 && mco::selected_iterations(true,0,-3)==0);
    assert(mco::selected_iterations(true,3,0)==2);
    assert(mco::pending_iterations(40,3)==16 && mco::pending_iterations(3,40)==0);
    assert(mco::pending_iterations(0,0xffffffffu)==1 && mco::pending_iterations(0x80000000u,0)==0);
    bool rejected=false;
    try { mco::execute_batch(0,3,false,[]{},[]{},[]{}); } catch(const std::invalid_argument&) {rejected=true;}
    assert(rejected);
}
