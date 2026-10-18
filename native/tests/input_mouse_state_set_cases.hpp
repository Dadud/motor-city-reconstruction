#pragma once
#include "mco/input_mouse_state_set.hpp"
#include "cell_io.hpp"
#include <vector>
namespace input_mouse_state_set_cases {
struct Fixture {
    std::array<std::uint32_t,3> config{};
    std::array<std::uint32_t,2> tables{};
    std::array<std::uint32_t,6> cooperative_targets{0,1,2,3,4,5};
    std::uint32_t cooperative{};
    std::vector<std::array<std::uint32_t,27>> logs;
    static std::uint32_t resolve(mco::InputMouseStateSet&,std::uint32_t id,void* user){
        auto& f=*static_cast<Fixture*>(user);
        if(id!=0x71001000 && id!=0x71001100)throw std::invalid_argument("mouse state identity");
        auto index=(id-0x71001000)/256;
        return 0x70009000+index*1024+f.tables[index]*256;
    }
    void mutate_device(mco::InputMouseStateSet& s){
        const auto index=(s.lifetime.words[12]-0x71001000)/256;
        if(index>=tables.size())throw std::invalid_argument("mouse mutation identity");
        tables[index]=1-tables[index];s.lifetime.words[12]=0x71001000+(1-index)*256;
    }
    static std::uint32_t invoke(mco::InputMouseStateSet& s,std::uint32_t code,std::uint32_t target,
        std::uint32_t id,std::span<const std::uint32_t> args,void* user){
        auto& f=*static_cast<Fixture*>(user);const auto profile=f.config[0],script=f.config[1],seed=f.config[2];
        auto& w=s.lifetime.words;
        if(target){if(code==0x34)target=0x70009000+f.cooperative_targets[(target-0x70009000)/256]*256;target+=code;}
        if(args.size()>2)throw std::invalid_argument("mouse state arguments");
        std::array<std::uint32_t,27> row{};row[0]=code;row[1]=target;row[2]=id;row[3]=static_cast<std::uint32_t>(args.size());
        for(unsigned i=0;i<args.size();++i)row[4+i]=args[i];
        for(unsigned i=0;i<15;++i)row[6+i]=w[i];
        row[21]=s.access_mode;row[22]=s.state8;row[23]=s.state9;
        row[24]=s.diagnostic_callback;row[25]=s.diagnostic_file;row[26]=s.diagnostic_line;
        f.logs.push_back(row);
        constexpr std::array<std::array<std::uint32_t,3>,6> profiles{{
            {0,0,0},{0x80004005,0,0},{0x80004005,1,0x80004005},
            {0x80004005,2,0},{1,0,1},{0xffffffff,0,0x8007001e}}};
        if(profile>=profiles.size())throw std::invalid_argument("mouse state profile");
        std::uint32_t result=0;
        if(code==0x584cf0){result=0xabcdef00+seed;if(script&128){const auto i=(w[12]-0x71001000)/256;f.cooperative_targets[i*4+f.tables[i]]^=1;}if(script&1)f.mutate_device(s);if(script&32){s.access_mode=0xf00d;w[4]=31;w[5]=37;}}
        else if(code==0x20){result=profiles[profile][1];if(script&2)f.mutate_device(s);}
        else if(code==0x34){result=profiles[profile][f.cooperative++==0?0:2];if(script&4)f.mutate_device(s);}
        else if(code==0x6f07f0){if(script&8){w[4]=0x80000000+seed;w[5]=0xffffffff-seed;s.access_mode=0x123;}}
        else if(code==0x7000b000){if(script&16){s.diagnostic_file=0xcafe;s.diagnostic_line=0xbeef;s.access_mode=0x333;}}
        if((code==0x1c || code==0x20 || code==0x34) && (script&64))w[11]=0;
        return result;
    }
    mco::InputMouseStateSetPlatform platform(){return {resolve,invoke,this};}
};
inline void compare(std::istream& in){
    Fixture f;for(auto& v:f.config)v=cell_io::read(in);
    const auto selector=cell_io::read(in),value=cell_io::read(in);
    std::array<std::uint32_t,15> words{};for(auto& v:words)v=cell_io::read(in);
    auto mode=cell_io::read(in),state8=cell_io::read(in),state9=cell_io::read(in);
    auto callback=cell_io::read(in),file=cell_io::read(in),line=cell_io::read(in);
    std::uint32_t width=640,height=480;mco::InputMouseLifetimeState lifetime{words,width,height};
    mco::InputMouseStateSet s{lifetime,mode,state8,state9,callback,file,line};
    for(unsigned i=0;i<2;++i)f.tables[i]=(f.config[2]+i)%2;
    const auto result=mco::input_mouse_state_set(s,f.platform(),selector,value);
    cell_io::emit(result);cell_io::emit(words);cell_io::emit(mode);cell_io::emit(state8);cell_io::emit(state9);
    cell_io::emit(callback);cell_io::emit(file);cell_io::emit(line);cell_io::emit(f.tables);
    cell_io::emit(static_cast<std::uint32_t>(f.logs.size()));for(const auto& row:f.logs)cell_io::emit(row);
}
}
