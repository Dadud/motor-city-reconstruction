#pragma once
#include "input_device_cases.hpp"
#include "mco/input_device_state.hpp"
#include <algorithm>
namespace input_device_state_cases {
struct Fixture {
    std::array<std::uint32_t,12> config{};
    std::array<std::byte,260> keyboard{};
    std::array<std::byte,540> information{};
    input_device_cases::Fixture methods;
    mco::InputDeviceBridge device{};
    mco::InputDeviceAccess* access{};
    std::array<std::uint32_t,4> globals{};
    std::vector<std::array<std::uint32_t,5>> logs;
    void initialize(){
        const auto seed=config[2];
        for(unsigned i=0;i<4;++i)keyboard[i]=static_cast<std::byte>((0x12345678u>>(i*8))&255);
        for(unsigned i=0;i<540;++i)information[i]=static_cast<std::byte>((seed+i*19)&255);
        methods.config={2,256,seed,config[3],config[4],config[5],config[6],config[7],config[8],config[9]};
        methods.buffer=std::span<std::byte>(keyboard).subspan(4);methods.initialize();
        device=methods.state();device.invoke=invoke;device.user=this;
    }
    void mutate(){
        if(config[11]&1)access->enabled=0;
        if(config[11]&2)access->device=0x71001100;
        if(config[11]&4){access->diagnostic_file=0x1234;access->diagnostic_line=0x4321;}
    }
    static std::uint32_t invoke(mco::InputDeviceBridge& device,std::uint32_t table,std::uint32_t method,std::span<std::byte> destination,std::uint32_t size,void* user){
        auto& f=*static_cast<Fixture*>(user);
        const auto result=input_device_cases::Fixture::invoke(device,table,method,destination,size,&f.methods);
        f.mutate();return result;
    }
    static mco::InputDeviceBridge& resolve(std::uint32_t identity,void* user){
        auto& f=*static_cast<Fixture*>(user);
        if(identity!=f.device.identity)throw std::invalid_argument("device resolution identity");
        return f.device;
    }
    static std::uint32_t info(mco::InputDeviceAccess& state,std::uint32_t identity,std::span<std::byte> output,void* user){
        auto& f=*static_cast<Fixture*>(user);
        f.logs.push_back({0,identity,0xb36240,state.diagnostic_file,state.diagnostic_line});
        for(unsigned i=0;i<output.size();++i)output[i]=static_cast<std::byte>((f.config[2]+i*17)&255);
        f.mutate();return f.config[10];
    }
    static void diagnostic(mco::InputDeviceAccess& state,std::uint32_t kind,void* user){
        auto& f=*static_cast<Fixture*>(user);
        f.logs.push_back({1,kind,0,state.diagnostic_file,state.diagnostic_line});f.mutate();
    }
    mco::InputDeviceAccess state(){
        globals={config[1],0x71001000,0x11223344,0x55667788};
        return {globals[0],globals[1],keyboard,information,globals[2],globals[3],resolve,info,diagnostic,this};
    }
    void emit(const mco::InputDeviceAccess& state){
        cell_io::emit(state.enabled);cell_io::emit(state.device);cell_io::emit(state.diagnostic_file);cell_io::emit(state.diagnostic_line);
        cell_io::emit(keyboard);cell_io::emit(information);
        cell_io::emit(device.table);for(auto byte:methods.buffer)cell_io::emit(std::to_integer<std::uint32_t>(byte));cell_io::emit(static_cast<std::uint32_t>(methods.logs.size()));
        for(const auto& row:methods.logs)for(auto v:row)cell_io::emit(v);
        cell_io::emit(static_cast<std::uint32_t>(logs.size()));for(const auto& row:logs)cell_io::emit(row);
    }
};
inline void compare(std::istream& input){
    Fixture f;for(auto& v:f.config)v=cell_io::read(input);f.initialize();auto state=f.state();f.access=&state;
    const auto result=mco::input_device_state(state,f.config[0]);
    cell_io::emit(result.empty()?0u:result.data()==f.keyboard.data()?0xb36460u:0xb36240u);f.emit(state);
}
}
