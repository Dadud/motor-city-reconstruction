#pragma once
#include "mco/input_callback_dispatch.hpp"
#include "cell_io.hpp"
#include <vector>
namespace input_callback_dispatch_cases {
struct Fixture {
    std::array<std::uint32_t,8> config{};
    mco::InputDeviceCallback callback{};
    std::uint32_t enabled{};
    std::array<std::byte,4> bytes{};
    std::vector<std::array<std::uint32_t,4>> logs;
    void initialize(){callback=config[1];callback.bind(bytes);enabled=config[2];}
    std::uint32_t observe(mco::InputCallbackDispatchState& state,unsigned kind,std::uint32_t identity){
        logs.push_back({kind,identity,state.callback,state.enabled});const auto script=config[6];
        if(kind==0){if(script&1)state.callback=0x7000e100;if(script&2)state.enabled=0;}
        else if(kind==1){if(script&4){state.callback=0;state.enabled=0x80000000;}}
        else if(script&8){state.callback=identity==0x7000e000?0x7000e100:0x7000e000;state.enabled^=1;}
        return config[3+kind];
    }
    static std::uint32_t available(mco::InputCallbackDispatchState& state,void* user){return static_cast<Fixture*>(user)->observe(state,0,0);}
    static std::uint32_t read(mco::InputCallbackDispatchState& state,void* user){return static_cast<Fixture*>(user)->observe(state,1,0);}
    static std::uint32_t invoke(mco::InputCallbackDispatchState& state,std::uint32_t identity,void* user){return static_cast<Fixture*>(user)->observe(state,2,identity);}
    mco::InputCallbackDispatchState state(){return {callback,enabled};}
    mco::InputCallbackDispatchPlatform platform(){return {available,read,invoke,this};}
    void emit(){
        cell_io::emit(callback);cell_io::emit(enabled);
        const auto word=static_cast<std::uint32_t>(callback);for(unsigned i=0;i<4;++i)cell_io::emit((word>>(i*8))&255u);cell_io::emit(static_cast<std::uint32_t>(logs.size()));
        for(const auto& row:logs)cell_io::emit(row);
    }
};
inline void compare(std::istream& input){
    Fixture f;for(auto& v:f.config)v=cell_io::read(input);f.initialize();auto state=f.state();
    if(f.config[0]>1)throw std::invalid_argument("callback comparison mode");
    cell_io::emit(f.config[0]==0?mco::input_callback_fallback(state,f.platform()):mco::input_callback_dispatch(state,f.platform()));f.emit();
}
}
