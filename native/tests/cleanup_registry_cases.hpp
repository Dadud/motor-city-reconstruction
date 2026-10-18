#pragma once
#include "mco/cleanup_registry.hpp"
#include "cell_io.hpp"
#include <vector>
namespace cleanup_registry_cases {
inline constexpr std::uint32_t first=0x7000e400,third=0x7000e600;
struct Fixture {
    std::array<std::uint32_t,64> slots{};
    mco::CleanupRegistry state{slots};
    std::uint32_t script{};
    std::vector<std::uint32_t> logs;
    static void invoke(mco::CleanupRegistry& state,std::uint32_t identity,void* user) {
        auto& f=*static_cast<Fixture*>(user);
        f.logs.push_back(identity);f.logs.push_back(0);
        f.logs.insert(f.logs.end(),state.slots.begin(),state.slots.end());
        if(f.script&1)state.slots[0]=0x7000e500;
        if(f.script&2)state.slots[63]=third;
        if(f.script&4)state.slots[31]=0;
        if(f.script&32)state.slots[1]=0;
        if(f.script&8)mco::cleanup_registry_register(state,first);
        if(f.script&16)mco::cleanup_registry_register(state,third);
        if(f.script&128)mco::cleanup_registry_register(state,0);
    }
    void emit() {
        cell_io::emit(slots);cell_io::emit(static_cast<std::uint32_t>(logs.size()/66));
        for(auto v:logs)cell_io::emit(v);
    }
};
inline void compare(std::istream& input) {
    const auto mode=cell_io::read(input);Fixture f;
    f.script=cell_io::read(input);const auto identity=cell_io::read(input);
    for(auto& slot:f.slots)slot=cell_io::read(input);
    if(mode==0)mco::cleanup_registry_register(f.state,identity);
    else if(mode==1)mco::cleanup_registry_run(f.state,{Fixture::invoke,&f});
    else throw std::invalid_argument("cleanup mode");
    f.emit();
}
}
