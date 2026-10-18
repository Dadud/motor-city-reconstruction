#pragma once
#include "cell_io.hpp"
#include "mco/input_scan_translate.hpp"
#include <vector>
namespace input_translation_cases {
struct ExitRequested {};
struct Fixture {
    std::array<std::uint32_t,11> config{};
    std::array<std::byte,260> device{};
    std::array<std::byte,620> tables{};
    std::vector<std::array<std::uint32_t,4>> logs;
    void initialize() {
        const auto scan=config[0],mask=config[2],value=config[3],seed=config[7],forced=config[8];
        if(scan>255 || value>255 || forced>256)throw std::invalid_argument("translation fixture range");
        for(unsigned i=0;i<device.size();++i)device[i]=static_cast<std::byte>((i*37+seed)&255);
        constexpr std::array<unsigned,6> modifiers{0x3c,0xbc,0x21,0xa1,0x2e,0x3a};
        for(unsigned i=0;i<6;++i)device[modifiers[i]]=static_cast<std::byte>((mask&(1u<<i)) ? value:0);
        for(unsigned i=0;i<tables.size();++i)tables[i]=static_cast<std::byte>((i*29+seed)&255);
        if(forced<256)for(unsigned i=0;i<5;++i)tables[i*91+scan]=static_cast<std::byte>(forced);
    }
    static std::span<const std::byte> get_state(mco::InputTranslationState& state,std::uint32_t kind,void* user) {
        auto& f=*static_cast<Fixture*>(user);f.logs.push_back({0,kind,state.caps,state.escape_exits});
        const auto mask=f.config[6];
        if(mask&1)state.caps^=1;
        if(mask&2)state.escape_exits^=1;
        if(mask&4)f.device[direct_key_image::alt_left]=std::byte{1};
        if(mask&8)for(unsigned i=0;i<5;++i)f.tables[i*91+f.config[0]]=static_cast<std::byte>(255-i);
        if(f.config[9])return f.device;
        return {};
    }
    static void exit_request(mco::InputTranslationState& state,std::uint32_t code,void* user) {
        auto& f=*static_cast<Fixture*>(user);f.logs.push_back({1,code,state.caps,state.escape_exits});
        throw ExitRequested{};
    }
    mco::InputTranslationState state() {return {config[4],config[5],tables,get_state,exit_request,this};}
};
inline void compare(std::istream& input) {
    Fixture f;for(auto& v:f.config)v=cell_io::read(input);f.initialize();auto state=f.state();
    std::uint32_t outcome=0,result=0;
    try {result=mco::input_scan_translate(state,f.config[0],f.config[1]);}
    catch(const ExitRequested&) {outcome=1;}
    cell_io::emit(outcome);cell_io::emit(result);cell_io::emit(state.caps);cell_io::emit(state.escape_exits);
    cell_io::emit(static_cast<std::uint32_t>(f.logs.size()));
    for(const auto& row:f.logs)cell_io::emit(row);
    if(f.config[10]) {cell_io::emit(f.device);cell_io::emit(f.tables);}
}
}
