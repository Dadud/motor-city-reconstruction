#pragma once
#include "mco/input_device_read.hpp"
#include "cell_io.hpp"
#include <vector>
namespace input_device_cases {
struct Fixture {
    std::array<std::uint32_t,10> config{};
    std::array<std::byte,64> storage{};
    std::span<std::byte> buffer{storage};
    std::array<unsigned,3> counts{};
    std::vector<std::vector<std::uint32_t>> logs;
    void initialize(){for(unsigned i=0;i<buffer.size();++i)buffer[i]=static_cast<std::byte>((config[2]+i*13)&255);}
    static std::uint32_t invoke(mco::InputDeviceBridge& device,std::uint32_t table,std::uint32_t method,std::span<std::byte> destination,std::uint32_t size,void* user) {
        auto& f=*static_cast<Fixture*>(user);
        unsigned index=method==0x64?0:method==0x1c?1:2;
        if(method!=0x64 && method!=0x1c && method!=0x24)throw std::invalid_argument("device method");
        std::vector<std::uint32_t> row{method,table,device.identity,size};
        for(auto byte:f.buffer)row.push_back(std::to_integer<unsigned>(byte));
        f.logs.push_back(std::move(row));
        const auto n=++f.counts[index];
        constexpr std::array<unsigned,3> starts{4,6,8};
        const auto status=f.config[starts[index]+(n>1?1:0)];
        if(method==0x24){
            if(size>destination.size())throw std::invalid_argument("fixture device destination");
            for(unsigned i=0;i<size;++i)destination[i]=static_cast<std::byte>((f.config[2]+f.logs.size()*37+i)&255);
        }
        if(f.config[3]&8)f.buffer.back()^=static_cast<std::byte>(f.logs.size());
        if(f.config[3]&(1u<<index))device.table=1-table;
        return status;
    }
    mco::InputDeviceBridge state(){return {0x71001000,config[2]&1,invoke,this};}
    std::uint32_t run(mco::InputDeviceBridge& device){
        if(config[0]==0)return mco::input_device_poll(device);
        if(config[0]==1)return mco::input_device_read_retry(device,buffer,config[1]);
        if(config[0]==2)return mco::input_device_read(device,buffer,config[1]);
        throw std::invalid_argument("device mode");
    }
};
inline void compare(std::istream& input){
    Fixture f;for(auto& v:f.config)v=cell_io::read(input);f.initialize();auto device=f.state();
    cell_io::emit(f.run(device));cell_io::emit(device.table);for(auto byte:f.buffer)cell_io::emit(std::to_integer<std::uint32_t>(byte));
    cell_io::emit(static_cast<std::uint32_t>(f.logs.size()));
    for(const auto& row:f.logs)for(auto v:row)cell_io::emit(v);
}
}
