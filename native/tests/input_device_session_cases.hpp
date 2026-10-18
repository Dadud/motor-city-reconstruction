#pragma once
#include "input_device_lifetime_cases.hpp"
#include "input_translation_cases.hpp"
#include "mco/input_device_lifetime_access.hpp"
#include "mco/input_translation_device_binding.hpp"
namespace input_device_session_cases {
struct Acquisition {
    input_device_lifetime_cases::Fixture& lifetime;
    mco::InputDeviceLifetimeState& state;
    std::array<std::byte,260> keyboard{};
    std::array<std::byte,540> information{};
    std::array<std::uint32_t,8> config{};
    std::array<unsigned,3> counts{};
    std::array<mco::InputDeviceBridge,2> devices{};
    std::vector<std::array<std::uint32_t,272>> logs;
    void initialize(){
        mco::detail::write_word(keyboard,0,0x12345678);
        for(unsigned i=0;i<256;++i)keyboard[4+i]=static_cast<std::byte>((config[6]+i*13)&255);
    }
    static mco::InputDeviceBridge& resolve(std::uint32_t identity,void* user){
        auto& f=*static_cast<Acquisition*>(user);
        if(identity!=0x71001200 && identity!=0x71001300)throw std::invalid_argument("session acquisition identity");
        const auto index=(identity-0x71001000)/256;
        auto& device=f.devices[index-2];device={identity,f.lifetime.tables[index],invoke,&f};return device;
    }
    static std::uint32_t invoke(mco::InputDeviceBridge& device,std::uint32_t table,std::uint32_t method,std::span<std::byte> output,std::uint32_t size,void* user){
        auto& f=*static_cast<Acquisition*>(user);const auto index=(device.identity-0x71001000)/256;
        const auto kind=method==0x64?0u:method==0x1c?1u:method==0x24?2u:3u;
        if(kind==3)throw std::invalid_argument("session acquisition method");
        std::array<std::uint32_t,272> row{};row[0]=method;row[1]=index;row[2]=table;row[3]=device.identity;row[4]=size;
        for(unsigned i=0;i<260;++i)row[5+i]=std::to_integer<std::uint32_t>(f.keyboard[i]);
        const auto values=input_device_lifetime_cases::Fixture::values(f.state);
        for(unsigned i=0;i<7;++i)row[265+i]=values[i];f.logs.push_back(row);
        const auto count=++f.counts[kind];const auto status=f.config[kind*2+(count>1?1:0)];
        if(method==0x24){
            if(size!=256 || output.data()!=f.keyboard.data()+4)throw std::invalid_argument("session read output");
            for(unsigned i=0;i<size;++i)output[i]=static_cast<std::byte>((f.config[6]+f.logs.size()*37+i)&255);
        }
        if(f.config[7]&1){device.table=1-table;f.lifetime.tables[index]=device.table;}
        return status;
    }
    void emit(const mco::InputTranslationState& translation,const input_translation_cases::Fixture& tables){
        cell_io::emit(keyboard);cell_io::emit(translation.caps);cell_io::emit(translation.escape_exits);cell_io::emit(tables.tables);
        cell_io::emit(static_cast<std::uint32_t>(logs.size()));for(const auto& row:logs)cell_io::emit(row);
    }
};
}
