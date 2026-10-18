#pragma once
#include "mco/input_device_lifetime.hpp"
#include "input_queue_cases.hpp"
#include <vector>
namespace input_device_lifetime_cases {
struct Fixture {
    std::array<std::uint32_t,7> config{};
    std::array<std::uint32_t,6> tables{};
    std::uint32_t* temporary{};
    std::vector<std::array<std::uint32_t,23>> logs;
    void initialize(){for(unsigned i=0;i<6;++i)tables[i]=(config[6]+i)&1;}
    static std::array<std::uint32_t,7> values(const mco::InputDeviceLifetimeState& s){return {s.interface_handle,s.device,s.initialized,s.cleanup_registered,s.callback,s.diagnostic_file,s.diagnostic_line};}
    static std::uint32_t invoke(mco::InputDeviceLifetimeState& s,std::uint32_t code,std::uint32_t identity,std::span<const std::uint32_t> args,std::uint32_t slot,std::uint32_t* output,void* user){
        auto& f=*static_cast<Fixture*>(user);const auto profile=f.config[4],script=f.config[5];
        std::uint32_t index=0,table=0xffffffff;
        if(identity!=0){
            if(identity<0x71001000 || identity>0x71001500 || (identity&255)!=0)throw std::invalid_argument("lifetime identity");
            index=(identity-0x71001000)/256;table=f.tables[index];
        }
        if(slot==2)f.temporary=output;
        if(args.size()>4)throw std::invalid_argument("lifetime argument count");
        std::array<std::uint32_t,23> row{};
        row[0]=code;row[1]=identity;row[2]=table;row[3]=slot;row[4]=static_cast<std::uint32_t>(args.size());
        for(unsigned i=0;i<args.size();++i)row[5+i]=args[i];
        row[9]=f.temporary?*f.temporary:f.config[3];const auto state=values(s);
        for(unsigned i=0;i<7;++i)row[10+i]=state[i];
        constexpr std::array<unsigned,6> offsets{0,4,0x4e0,0x4a8,0x524,0x4c4};
        for(unsigned i=0;i<6;++i)row[17+i]=s.queue.load(offsets[i]);f.logs.push_back(row);
        std::uint32_t status=0;
        if(code==0x100){
            status=0x12345678;
            if(script&8){s.initialized=9;s.queue.store(0,7);s.queue.store(4,2);s.queue.store(0x4e0,1);s.queue.store(0x4a8,3);}
        }else if(code==0x101){
            status=0x400000;if(script&32){s.interface_handle=0x71001100;s.device=0x71001300;}
        }else if(code==0x102){
            *output=profile==6?0:0x71001000;status=(profile==1 || profile==6)?0x80004005:0;
        }else if(code==0xc){
            if(profile!=7)*output=0x71001400;status=(profile==2 || profile==7)?0x80004005:0;
        }else if(code==0){
            if(profile!=8)*output=0x71001200;status=(profile==3 || profile==8)?0x80004005:0;
            if(script&128)*f.temporary=0x71001500;
        }else if(code==0x2c){
            status=profile==4?0x80004005:0;if(script&64){s.device=0x71001300;s.queue.store(0x4c4,0xdeadbeef);}
        }else if(code==0x34){status=profile==5?0x80004005:0;
        }else if(code==0x20){
            status=0x80004005;if(script&1){s.device=0x71001300;s.interface_handle=0x71001100;}
        }else if(code==8){
            status=0xdeadbeef;if(script&2){s.device=0x71001300;s.interface_handle=0x71001100;}
        }else if(code==0x103){
            status=0xffffffff;if(script&16){s.initialized=0x1234;s.cleanup_registered=0x5678;}
        }else if(code==0x104){
            status=0xdeadbeef;if(script&256)s.initialized=555;
        }else throw std::invalid_argument("lifetime call code");
        if(table!=0xffffffff && (script&4))f.tables[index]=1-table;
        return status;
    }
    mco::InputDeviceLifetimePlatform platform(){return {invoke,this};}
    std::uint32_t run(mco::InputDeviceLifetimeState& s){
        temporary=nullptr;
        switch(config[0]){
        case 0:mco::input_device_cleanup(s,platform());return 0;
        case 1:mco::input_device_shutdown(s,platform());return 0;
        case 2:return mco::input_device_set_state(s,platform(),config[1],config[2]);
        case 3:return mco::input_device_window(s.queue);
        case 4:return mco::input_device_initialize(s,platform(),config[3]);
        default:throw std::invalid_argument("lifetime mode");
        }
    }
    void emit(const mco::InputDeviceLifetimeState& state,const queue_cases::Fixture& queue){
        cell_io::emit(values(state));queue.emit();cell_io::emit(tables);cell_io::emit(static_cast<std::uint32_t>(logs.size()));
        for(const auto& row:logs)cell_io::emit(row);
    }
};
inline void compare(std::istream& input){
    Fixture f;for(auto& v:f.config)v=cell_io::read(input);f.initialize();
    std::array<std::uint32_t,7> values;for(auto& v:values)v=cell_io::read(input);
    auto queue=queue_cases::Fixture::read(input);auto q=queue.state();
    mco::InputDeviceLifetimeState s{q,values[0],values[1],values[2],values[3],values[4],values[5],values[6]};
    cell_io::emit(f.run(s));f.emit(s,queue);
}
}
