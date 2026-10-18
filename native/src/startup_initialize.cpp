#include "mco/startup_initialize.hpp"
#include <bit>
#include <initializer_list>
#include <stdexcept>
namespace mco {
void startup_window_policy(StartupState& state,std::uint32_t flag,std::uint32_t callback){
    state.queue.store(input_queue_image::policy_flag,flag);
    state.at(StartupGlobal::policy_callback)=callback;
    state.queue.store(input_queue_image::policy_enabled,1);
}
void startup_initialize(StartupState& state,const StartupPlatform& platform){
    using G=StartupGlobal;
    auto call=[&](std::uint32_t identity,std::initializer_list<std::uint32_t> args=std::initializer_list<std::uint32_t>{}){
        if(!platform.invoke)throw std::invalid_argument("startup subsystem bridge required");
        return platform.invoke(state,identity,{args.begin(),args.size()},platform.user);
    };
    auto nonempty=[&](std::uint32_t identity){
        if(identity==0)return false;
        if(!platform.driver_nonempty)throw std::invalid_argument("startup driver-name view required");
        return platform.driver_nonempty(identity,platform.user);
    };
    auto diagnostic=[&](std::uint32_t line,std::uint32_t message){
        state.at(G::diagnostic_file)=0x847bd4;state.at(G::diagnostic_line)=line;
        call(state.at(G::diagnostic_callback),{message});
    };
    call(0x6bedf0);
    state.at(G::diagnostic_file)=0x847bd4;state.at(G::diagnostic_line)=0x38;
    if(state.at(G::diagnostic_callback)==0)call(0x6bda50);
    call(0x699284,{0x6bf410});call(0x6be4f0,{0});
    if(state.at(G::auxiliary_ready)==0)call(0x6eed30);
    call(0x6bd2e0,{state.at(G::configuration)});call(0x6bdd10);call(0x6f3860);
    if(state.at(G::graphics_ready)==0){
        call(0x6bf9b0,{0x89860c,0x8e3ac4,0});call(0x6bf9b0,{0x8985f4,0x8e3ac4,0});
        call(0x6bf9b0,{0x8985e0,0x88b7ac,1});call(0x6bf9b0,{0x8985d0,0x88b7ac,1});call(0x6bf9b0,{0x8985c0,0x88b7ac,1});
        if(!nonempty(state.at(G::driver_name)))state.at(G::driver_name)=call(0x6d0f20);
        state.at(G::driver_loaded)=0;
        if(state.at(G::external_driver)==0){
            if(!nonempty(state.at(G::driver_name)))state.at(G::driver_name)=0x896bc0;
            state.at(G::driver_loaded)=1;
            if(call(0x6d0820,{state.at(G::driver_name)})==0)diagnostic(0x66,0x847b9c);
        }
        if(call(0x6d0cd0,{state.at(G::width),state.at(G::height),state.at(G::depth),state.at(G::mode),state.at(G::flags)})==0)diagnostic(0x6a,0x847b70);
        if(state.at(G::graphics_ready)==0)return;
    }
    call(0x6c1c80);startup_window_policy(state,1,0x6bfc60);
    call(0x6ef890);call(0x6bfc80);call(0x6f0200);call(0x6f09f0);call(0x6f0360,{10,0x6f0580});
    call(0x6e24f0,{0x6ee510,0x6ee550});call(0x6e2510,{0,0,0});call(0x6e8d40);
    call(0x6f2de0,{0,0,state.at(G::width),state.at(G::height),0,0x477fff00,0x3db60b61});call(0x6cb710,{3});
    const auto width=std::bit_cast<std::uint32_t>(static_cast<float>(std::bit_cast<std::int32_t>(state.at(G::width))));
    const auto height=std::bit_cast<std::uint32_t>(static_cast<float>(std::bit_cast<std::int32_t>(state.at(G::height))));
    call(0x6cb610,{0,0,width,height,0x3f800000,0x37800000});
}
}
