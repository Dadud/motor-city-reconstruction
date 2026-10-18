#pragma once
#include "mco/input_mouse_runtime_binding.hpp"
#include "mco/window_message_dispatch.hpp"
#include "input_mouse_lifetime_cases.hpp"
#include <algorithm>
namespace input_mouse_runtime_cases {
using namespace mco;
struct Fixture {
    input_mouse_lifetime_cases::Fixture backend;
    std::vector<std::array<std::uint32_t,11>> events;
    InputMouseRuntimeBinding* binding{};
    unsigned cooperative{},queries{};
    void event(std::uint32_t code,std::initializer_list<std::uint32_t> args){
        std::array<std::uint32_t,11> row{};row[0]=code;row[2]=0xffffffff;row[4]=static_cast<std::uint32_t>(args.size());
        unsigned i=5;for(auto a:args)row[i++]=a;events.push_back(row);
    }
    static std::uint32_t external(InputMouseLifetimeState& s,std::uint32_t code,std::uint32_t id,
        std::span<const std::uint32_t> args,std::uint32_t slot,std::span<std::uint32_t> out,void* user){
        auto& f=*static_cast<Fixture*>(user);
        auto result=input_mouse_lifetime_cases::Fixture::invoke(s,code,id,args,slot,out,&f.backend);
        std::array<std::uint32_t,11> row{};std::copy_n(f.backend.logs.back().begin(),11,row.begin());f.events.push_back(row);
        if(code==0x34)result=f.backend.config[1]==6 && f.cooperative++%2==0?0x80004005:0;
        return result;
    }
    static std::uint32_t resolve(InputMouseStateSet&,std::uint32_t id,void* user){
        auto& f=*static_cast<Fixture*>(user);const auto i=(id-0x71001000)/256;
        if(i>=6)throw std::invalid_argument("runtime COM identity");return 0x71006000+i*512+f.backend.tables[i]*256;
    }
    static std::uint32_t state_call(InputMouseStateSet& s,std::uint32_t code,std::uint32_t,std::uint32_t id,std::span<const std::uint32_t> args,void* u){
        return external(s.lifetime,code,id,args,0,{},u);
    }
    static void sync(WindowDispatchState&,bool entering,std::uint32_t id,void* u){static_cast<Fixture*>(u)->event(entering?0x83b270:0x83b274,{id});}
    static std::uint32_t convert(std::uint32_t window,std::uint32_t& x,std::uint32_t& y,void* u){
        auto& f=*static_cast<Fixture*>(u);f.event(0x83b45c,{window,x,y});x+=100;y+=200;return f.backend.config[1]!=7;
    }
    static void position(std::uint32_t x,std::uint32_t y,void* u){static_cast<Fixture*>(u)->event(0x83b384,{x,y});}
    static void cursor(std::uint32_t id,void* u){static_cast<Fixture*>(u)->event(0x83b434,{id});}
    static std::uint32_t context(InputMouseGeometryState&,std::uint32_t code,std::uint32_t arg,void* u){
        auto& f=*static_cast<Fixture*>(u);
        if(code==0x6be930 || code==0x8c4938)f.event(code,{arg});else f.event(code,{});
        return code==0x6be930?(f.backend.config[3]+f.queries++)%2:0;
    }
    static std::uint32_t dispatch(WindowDispatchState&,std::uint32_t handler,std::uint32_t owner,std::uint32_t window,std::uint32_t,std::uint32_t wparam,std::uint32_t,std::uint32_t,void* u){
        auto& f=*static_cast<Fixture*>(u);if(handler!=0x6efa60)throw std::invalid_argument("runtime mouse handler");
        return input_mouse_wheel(f.binding->callbacks,owner,window,wparam);
    }
};
inline void emit(std::uint32_t result,InputMouseRuntimeBinding& b,Fixture& f){
    auto& lifetime=b.callbacks.lifetime;auto& mouse=b.geometry.mouse;
    cell_io::emit(result);cell_io::emit(lifetime.words);cell_io::emit(lifetime.width);cell_io::emit(lifetime.height);
    cell_io::emit(mouse.enabled);cell_io::emit(mouse.button_callback);for(unsigned j=0;j<7;++j)cell_io::emit(mouse.load(j*4));
    cell_io::emit(b.geometry.position_x);cell_io::emit(b.geometry.position_y);cell_io::emit(b.callbacks.reported_buttons);
    cell_io::emit(b.callbacks.wheel);cell_io::emit(b.callbacks.counter);cell_io::emit(b.callbacks.callback_ids);
    cell_io::emit(mouse.window.load(input_queue_image::target_window));
    cell_io::emit(b.setter.access_mode);cell_io::emit(b.setter.state8);cell_io::emit(b.setter.state9);
    cell_io::emit(b.setter.diagnostic_callback);cell_io::emit(b.setter.diagnostic_file);cell_io::emit(b.setter.diagnostic_line);
    for(auto v:mouse.window.globals)cell_io::emit(static_cast<std::uint32_t>(v));
    for(auto v:b.registry.slots)cell_io::emit(v);cell_io::emit(f.backend.tables);
    cell_io::emit(static_cast<std::uint32_t>(f.events.size()));
    for(const auto& row:f.events)cell_io::emit(row);f.events.clear();
}
}
