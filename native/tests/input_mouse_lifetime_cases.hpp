#pragma once
#include "mco/input_mouse_lifetime.hpp"
#include "cell_io.hpp"
#include <vector>
namespace input_mouse_lifetime_cases {
struct Fixture {
    std::array<std::uint32_t,4> config{};
    std::array<std::uint32_t,6> tables{};
    std::uint32_t* temporary{};
    std::vector<std::array<std::uint32_t,28>> logs;
    static std::uint32_t invoke(mco::InputMouseLifetimeState& s,std::uint32_t code,std::uint32_t id,
      std::span<const std::uint32_t> input,std::uint32_t slot,std::span<std::uint32_t> out,void* user){
        auto& f=*static_cast<Fixture*>(user);auto& w=s.words;
        const auto profile=f.config[1],script=f.config[2],seed=f.config[3];
        unsigned index=0;std::uint32_t table=0xffffffff;
        if(id){
            if(id<0x71001000 || id>0x71001500 || (id&255))throw std::invalid_argument("mouse lifetime identity");
            index=(id-0x71001000)/256;table=f.tables[index];
        }
        if(slot==2)f.temporary=out.data();
        std::vector<std::uint32_t> args(input.begin(),input.end());
        if(code==0x103){args.push_back(out[0]);args.push_back(out[1]);}
        if(args.size()>6)throw std::invalid_argument("mouse lifetime argument count");
        std::array<std::uint32_t,28> row{};row[0]=code;row[1]=id;row[2]=table;row[3]=slot;row[4]=static_cast<std::uint32_t>(args.size());
        for(unsigned i=0;i<args.size();++i)row[5+i]=args[i];
        for(unsigned i=0;i<15;++i)row[11+i]=w[i];row[26]=s.width;row[27]=s.height;f.logs.push_back(row);
        std::uint32_t result=0;
        if(code==0x6f06c0 && (script&1))w[13]=9;
        else if(code==0x100){result=0x400000;if(script&2){w[11]=0x71001100;w[12]=0x71001300;}}
        else if(code==0x101){out[0]=0x71001000;result=profile==1?0x80004005:0;}
        else if(code==0xc){out[0]=0x71001400;result=profile==2?0x80004005:0;}
        else if(code==0){out[0]=0x71001200;result=profile==3?0x80004005:0;if(script&128)*f.temporary=0x71001500;}
        else if(code==0x2c)result=profile==4?0x80004005:0;
        else if(code==0x18)result=profile==5?0x80004005:0;
        else if(code==0x20){if(script&4){w[12]=0x71001300;w[11]=0x71001100;}}
        else if(code==8){if(script&8){w[12]=0x71001300;w[11]=0x71001100;}}
        else if(code==0x6efaf0){if(script&16){w[11]=0x71001000;s.width=0x80000000+seed;s.height=0x1000001+seed;}}
        else if(code==0x6bf450){if(script&32){w[13]=0;w[14]=0xdeadbeef;}}
        else if(code==0x102){out[0]=0x80000000+seed;out[1]=0xffffffff-seed;result=profile!=7;}
        else if(code==0x103){out[0]+=17;out[1]+=31;result=profile!=6;}
        else if(code==0x584cf0){result=0xabcdef00+seed;if(script&64)w[13]=7;}
        if(table!=0xffffffff && (script&1))f.tables[index]=1-table;
        return result;
    }
    mco::InputMouseLifetimePlatform platform(){return {invoke,this};}
};
inline void compare(std::istream& in){
    Fixture f;for(auto& v:f.config)v=cell_io::read(in);
    std::array<std::uint32_t,15> words{};for(auto& v:words)v=cell_io::read(in);
    auto width=cell_io::read(in),height=cell_io::read(in);
    std::array<std::uint32_t,6> args{};for(auto& v:args)v=cell_io::read(in);
    for(unsigned i=0;i<6;++i)f.tables[i]=(f.config[3]+i)%2;
    mco::InputMouseLifetimeState s{words,width,height};std::uint32_t result=0;
    if(f.config[0]==0)result=mco::input_mouse_lifetime(s,f.platform(),0x71001400);
    else if(f.config[0]==1)mco::input_mouse_cleanup(s,f.platform());
    else if(f.config[0]==2)mco::input_mouse_bounds(s,f.platform(),args);
    else throw std::invalid_argument("mouse lifetime mode");
    cell_io::emit(result);cell_io::emit(words);cell_io::emit(width);cell_io::emit(height);cell_io::emit(f.tables);
    cell_io::emit(static_cast<std::uint32_t>(f.logs.size()));for(const auto& row:f.logs)cell_io::emit(row);
}
}
