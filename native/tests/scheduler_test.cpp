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
    const auto game=mco::build_game_task_lists({0x1000,0x2000},{0x3000},{3,4},0x4000,2);
    assert(game.primary_capacity==25 && game.secondary_capacity==17);
    const std::vector<mco::ScheduledCall> expected_primary{
        {6,0x520c20,0x1000},{6,0x520c20,0x2000},{6,0x520c20,0x3000},{6,0x42d730,0},
        {8,0x43f550,0},{10,0x487790,0x4000},{0x15,0x469010,0x1000},{0x15,0x469010,0x2000},
        {0x1e,0x53c140,0x1000},{0x1e,0x53c140,0x2000},{0x1e,0x5779d0,0x3000},
        {0x1e,0x4265f0,0},{0x1e,0x426730,0},{0x28,0x45abe0,0x1000},
        {0x28,0x45abe0,0x2000},{0x28,0x4265b0,0},{0x28,0x45abe0,0x3000},
        {0x32,0x43d6e0,0x1000},{0x32,0x43d6e0,0x2000},{0x32,0x424ec0,0},
        {0x32,0x426770,0},{100,0x55f520,0},{0x6e,0x55d300,0},{0x78,0x5678f0,0}};
    const std::vector<mco::ScheduledCall> expected_secondary{
        {6,0x42d780,0},{6,0x459df0,0},{0x19,0x585790,0x1000},{0x19,0x585790,0x2000},
        {0x1e,0x520450,0x1000},{0x1e,0x520450,0x2000},{0x1e,0x520450,0x3000},
        {0x23,0x40adb0,0},{100,0x43f9d0,0x1000},{100,0x43f9d0,0x2000},
        {100,0x55f540,0},{0x6e,0x5850b0,0}};
    auto same=[](const auto& actual,const auto& expected) {
        if(actual.size()!=expected.size()) return false;
        for(std::size_t i=0;i<actual.size();++i)
            if(actual[i].priority!=expected[i].priority || actual[i].callback!=expected[i].callback ||
               actual[i].payload!=expected[i].payload) return false;
        return true;
    };
    assert(same(game.primary,expected_primary) && same(game.secondary,expected_secondary));
    const auto conditional=mco::build_game_task_lists({0x1000,0x2000,0x3000,0x4000},{},
        {1,2,3,4},0,0);
    std::vector<std::uint32_t> selected;
    for(const auto& entry:conditional.secondary)
        if(entry.callback==0x585790) selected.push_back(entry.payload);
    assert((selected==std::vector<std::uint32_t>{0x3000,0x4000}));
    bool rejected=false;
    try { (void)mco::build_game_task_lists({}, {}, {}, 0, 0x7fffffff); }
    catch(const std::invalid_argument&) { rejected=true; }
    assert(rejected);
    rejected=false;
    try { mco::execute_batch(0,3,false,[]{},[]{},[]{}); } catch(const std::invalid_argument&) {rejected=true;}
    assert(rejected);
}
