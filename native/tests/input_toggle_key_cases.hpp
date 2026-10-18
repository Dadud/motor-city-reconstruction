#pragma once
#include "mco/input_toggle_key.hpp"
#include <array>
#include <vector>
#include <iostream>
#include <stdexcept>
namespace input_toggle_key_cases {
struct Calls {
    std::uint32_t state{},script{};
    std::vector<std::array<std::uint32_t,6>> logs;
    mco::InputToggleKeyPlatform platform{query,first,this};
    static std::uint32_t query(std::uint32_t key,void* p){
        auto& f=*static_cast<Calls*>(p);f.logs.push_back({0,0,key,0,0,0});
        if(f.script&1)f.platform.event=second;
        return f.state;
    }
    static void event(bool alt,std::uint32_t key,std::uint32_t scan,std::uint32_t flags,std::uint32_t extra,void* p){
        auto& f=*static_cast<Calls*>(p);f.logs.push_back({1,alt?1u:0u,key,scan,flags,extra});
        if(f.script&2)f.platform.event=alt?first:second;
    }
    static void first(std::uint32_t a,std::uint32_t b,std::uint32_t c,std::uint32_t d,void* p){event(false,a,b,c,d,p);}
    static void second(std::uint32_t a,std::uint32_t b,std::uint32_t c,std::uint32_t d,void* p){event(true,a,b,c,d,p);}
};
inline void compare(std::istream& input){
    std::uint32_t mode,selector,desired;Calls f;
    if(!(input>>mode>>selector>>desired>>f.state>>f.script))throw std::runtime_error("toggle-key input");
    if(mode==0)mco::input_toggle_key(selector,desired,f.platform);
    else if(mode==1)mco::input_startup_numlock(f.platform);
    else throw std::runtime_error("toggle-key mode");
    std::cout<<f.logs.size();for(const auto& row:f.logs)for(auto v:row)std::cout<<' '<<v;
}
}
