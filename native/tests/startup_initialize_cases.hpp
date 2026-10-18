#pragma once
#include "mco/startup_initialize.hpp"
#include "input_queue_cases.hpp"
namespace startup_initialize_cases {
inline constexpr std::uint32_t diag0=0x7000e900,diag1=0x7000ea00,empty=0x71005000,name=0x71005010;
struct Fixture {
    std::array<std::uint32_t,6> config{};
    std::array<std::uint32_t,mco::startup_global_count> values{};
    std::vector<std::array<std::uint32_t,26>> logs;
    unsigned env_calls{};
    static bool nonempty(std::uint32_t identity,void*) {
        if(identity==empty)return false;
        if(identity==name || identity==0x896bc0)return true;
        throw std::invalid_argument("startup driver identity");
    }
    static std::uint32_t invoke(mco::StartupState& state,std::uint32_t id,std::span<const std::uint32_t> args,void* user) {
        auto& f=*static_cast<Fixture*>(user);using G=mco::StartupGlobal;
        if(args.size()>7)throw std::invalid_argument("startup argument count");
        std::array<std::uint32_t,26> row{};row[0]=id;row[1]=static_cast<std::uint32_t>(args.size());
        for(unsigned i=0;i<args.size();++i)row[2+i]=args[i];
        for(unsigned i=0;i<mco::startup_global_count;++i)row[9+i]=state.globals[i];
        row[24]=state.queue.load(input_queue_image::policy_enabled);row[25]=state.queue.load(input_queue_image::policy_flag);f.logs.push_back(row);
        const auto script=f.config[0],seed=f.config[5];auto result=0x11110000u+(id&65535u);
        if(id==0x6bedf0 && (script&1))state.at(G::diagnostic_callback)=diag1;
        else if(id==0x6bda50)state.at(G::diagnostic_callback)=(script&2)?diag1:diag0;
        else if(id==0x6be4f0 && (script&4)){state.at(G::auxiliary_ready)=0;state.at(G::configuration)=0x12340000+seed;}
        else if(id==0x6f3860 && (script&8))state.at(G::graphics_ready)^=1;
        else if(id==0x6bf9b0){++f.env_calls;if((script&16) && f.env_calls%5==1){state.at(G::driver_name)=empty;state.at(G::external_driver)^=1;}}
        else if(id==0x6d0f20){result=f.config[1];if(script&32){state.at(G::external_driver)^=1;state.at(G::driver_name)=name;}}
        else if(id==0x6d0820){result=f.config[2];if(script&64){state.at(G::width)=0x1000001;state.at(G::height)=0x80000001;}}
        else if(id==0x6d0cd0){result=f.config[3];state.at(G::graphics_ready)=f.config[4];if(script&256){state.at(G::driver_loaded)=0xabcdef01;state.at(G::height)^=0xffffffff;}}
        else if((id==diag0 || id==diag1) && (script&128)){state.at(G::diagnostic_file)=0x11223344;state.at(G::diagnostic_line)=0x55667788;state.at(G::graphics_ready)^=1;state.at(G::diagnostic_callback)=id==diag0?diag1:diag0;++state.at(G::width);}
        else if(id==0x6e8d40 && (script&512)){state.at(G::width)=0x1000001+seed;state.at(G::height)=0x7fffffff-seed;}
        else if(id==0x6cb710 && (script&1024)){state.at(G::width)=0x80000000+seed;state.at(G::height)=0x1000001+seed;}
        else if(id==0x6f0200 && (script&2048)){state.queue.store(input_queue_image::raw_mode,7);state.queue.store(input_queue_image::policy_flag,0xabcdef02);}
        return result;
    }
    mco::StartupPlatform platform(){return {invoke,nonempty,this};}
    void emit(const mco::StartupState& state)const {
        for(auto v:state.globals)cell_io::emit(v);cell_io::emit(static_cast<std::uint32_t>(logs.size()));
        for(const auto& row:logs)cell_io::emit(row);
    }
};
inline void compare(std::istream& input){
    const auto mode=cell_io::read(input);Fixture f;for(auto& v:f.config)v=cell_io::read(input);for(auto& v:f.values)v=cell_io::read(input);
    auto queue=queue_cases::Fixture::read(input);auto q=queue.state();mco::StartupState state{q,f.values};
    const auto flag=cell_io::read(input),callback=cell_io::read(input);
    if(mode==0)mco::startup_initialize(state,f.platform());
    else if(mode==1)mco::startup_window_policy(state,flag,callback);
    else throw std::invalid_argument("startup mode");
    queue.emit();f.emit(state);
}
}
