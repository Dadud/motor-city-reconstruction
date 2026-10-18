#pragma once
#include "mco/input_device_information.hpp"
#include "mco/detail/byte_words.hpp"
#include "cell_io.hpp"
#include <vector>
#include <utility>
namespace input_device_information_cases {
struct Fixture {
    std::array<std::uint32_t,12> config{};
    std::array<std::byte,540> storage{};
    std::span<std::byte,540> output{storage};
    std::array<std::uint32_t,8> axes{};
    std::span<std::byte> caps;
    unsigned objects{};
    std::vector<std::vector<std::uint32_t>> logs;
    void initialize(){
        for(unsigned i=0;i<540;++i)output[i]=static_cast<std::byte>((config[7]+i*37)&255);
        for(unsigned i=0;i<8;++i)axes[i]=0x100+i*0x11;
    }
    static std::uint32_t invoke(mco::InputDeviceBridge& device,std::uint32_t table,std::uint32_t method,std::span<std::byte> record,std::uint32_t selector,std::uint32_t flags,void* user){
        using mco::detail::read_word;using mco::detail::write_word;
        auto& f=*static_cast<Fixture*>(user);const auto& c=f.config;const auto script=c[11];
        std::vector<std::uint32_t> row{method,table,device.identity,selector,flags,read_word(record,0)};
        for(auto b:f.output)row.push_back(std::to_integer<std::uint32_t>(b));
        for(auto v:f.axes)row.push_back(v);f.logs.push_back(std::move(row));
        std::uint32_t status=0;
        if(method==0x3c){
            for(unsigned i=0;i<record.size();++i)record[i]=static_cast<std::byte>((c[7]+i*23)&255);
            write_word(record,0,580);write_word(record,36,c[0]);
            for(const auto [offset,length]:std::array<std::pair<unsigned,unsigned>,2>{{{40,c[8]},{300,c[9]}}}){
                for(unsigned i=0;i<260;++i)record[offset+i]=static_cast<std::byte>((c[7]+i*7)%255+1);
                if(length<260)record[offset+length]=std::byte{};
            }
            status=c[5];
        }else if(method==0xc){
            f.caps=record;
            for(unsigned i=0;i<record.size();++i)record[i]=static_cast<std::byte>((c[7]+i*23)&255);
            write_word(record,0,44);write_word(record,4,c[1]);write_word(record,12,c[2]);write_word(record,16,c[3]);write_word(record,20,c[4]);
            status=c[6];if(script&8)write_word(f.output,4,0xa5a5a5a5);
        }else if(method==0x38){
            const auto n=++f.objects;
            for(unsigned i=0;i<record.size();++i)record[i]=static_cast<std::byte>((c[7]+n*11+i*23)&255);
            write_word(record,0,script&32?316+n:316);
            const std::array<bool,4> success{true,false,n%2==0,(selector+c[7]+n)%3==0};
            if(c[10]>3)throw std::invalid_argument("information fixture pattern");
            status=success[c[10]]?0:0x80004005;
            if(script&2){const auto type=read_word(f.output,0);write_word(f.output,0,(type&0xffffff00u)|((type&255)==2?4u:2u));}
            if((script&4) && n==1){write_word(f.caps,16,0);write_word(f.caps,12,2);write_word(f.caps,20,1);}
            if(script&8)write_word(f.output,12,read_word(f.output,12)^0x80000000u);
            if(script&16)f.axes[n&7]^=0xdead0000u+n;
        }else throw std::invalid_argument("information method");
        if(script&1)device.table=1-table;
        return status;
    }
    mco::InputDeviceBridge device(){return {0x71001000,config[7]&1,nullptr,nullptr};}
    mco::InputDeviceInformationBridge platform(){return {axes,invoke,this};}
    void emit(const mco::InputDeviceBridge& device){
        cell_io::emit(device.table);for(auto b:output)cell_io::emit(std::to_integer<std::uint32_t>(b));cell_io::emit(axes);
        cell_io::emit(static_cast<std::uint32_t>(logs.size()));for(const auto& row:logs)for(auto v:row)cell_io::emit(v);
    }
};
inline void compare(std::istream& input){
    Fixture f;for(auto& v:f.config)v=cell_io::read(input);f.initialize();auto device=f.device();
    cell_io::emit(mco::input_device_information(device,f.platform(),f.output));f.emit(device);
}
}
