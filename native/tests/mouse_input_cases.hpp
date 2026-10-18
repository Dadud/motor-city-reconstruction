#pragma once
#include "cell_io.hpp"
#include "mco/input_cursor_warp.hpp"
#include "mco/input_mouse_update.hpp"
#include "mco/input_mouse_press.hpp"
#include "mco/input_mouse_motion.hpp"
#include <vector>
namespace mouse_input_cases {
struct Fixture {
    std::uint32_t mask,value,success,cx,cy;
    mco::MouseInputState* mouse{};
    std::vector<std::array<std::uint32_t,16>> logs;
    std::uint32_t creations{};
    const mco::MousePlatformBridge* platform{};
    void observe(std::uint32_t kind,std::uint32_t a=0,std::uint32_t b=0,std::uint32_t c=0,std::uint32_t d=0) {
        std::array<std::uint32_t,16> row{kind,a,b,c,d,mouse->enabled,mouse->button_callback,
            mouse->window.load(input_queue_image::dispatch_synchronizer),mouse->window.load(input_queue_image::target_window)};
        for(unsigned i=0;i<7;++i) row[9+i]=mouse->load(i*4);
        logs.push_back(row);
    }
    static void sync(mco::WindowDispatchState& window,bool entering,std::uint32_t identity,void* user) {
        auto& f=*static_cast<Fixture*>(user);auto& m=*f.mouse;
        f.observe(entering ? 1:2,identity);
        if(entering) {
            if(f.mask&1) {m.enabled=0;for(unsigned i=0;i<4;++i)m.store(i*4,0x7fffffff);}
            if(f.mask&2) window.store(input_queue_image::dispatch_synchronizer,window.load(input_queue_image::dispatch_synchronizer)^f.value);
            if(f.mask&4) m.button_callback=0;
            if(f.mask&512) m.store(mouse_input_image::buttons,f.value);
        } else {
            if(f.mask&64) {m.button_callback=0x7000a100;m.enabled=0;}
            if(f.mask&256) m.button_callback=0;
        }
    }
    static std::uint32_t convert(std::uint32_t window,std::uint32_t& x,std::uint32_t& y,void* user) {
        auto& f=*static_cast<Fixture*>(user);auto& m=*f.mouse;
        f.observe(3,window,x,y);x=f.cx;y=f.cy;
        if(f.mask&8) {
            m.window.store(input_queue_image::target_window,m.window.load(input_queue_image::target_window)^f.value);
            m.store(mouse_input_image::x,f.value^0x1100);m.store(mouse_input_image::y,f.value^0x2200);
        }
        return f.success;
    }
    static void position(std::uint32_t x,std::uint32_t y,void* user) {
        auto& f=*static_cast<Fixture*>(user);f.observe(4,x,y);
        if(f.mask&16) f.mouse->store(mouse_input_image::buttons,f.value);
    }
    static void cursor(std::uint32_t identity,void* user) {
        auto& f=*static_cast<Fixture*>(user);f.observe(5,identity);
        if(f.mask&32) {f.mouse->store(mouse_input_image::x,f.value^0x3300);f.mouse->store(mouse_input_image::y,f.value^0x4400);}
    }
    static void notify(std::uint32_t identity,std::uint32_t buttons,void* user) {
        auto& f=*static_cast<Fixture*>(user);auto& m=*f.mouse;f.observe(6,identity,buttons);
        if(f.mask&128) {
            m.button_callback=0;m.window.store(input_queue_image::dispatch_synchronizer,m.window.load(input_queue_image::dispatch_synchronizer)^f.value);
            m.store(mouse_input_image::buttons,m.load(mouse_input_image::buttons)^1u);
        }
    }
};
struct Sample {
    std::array<std::byte,input_queue_image::size> globals{};
    std::array<std::byte,mouse_input_image::size> image{};
    Fixture script{0,0x11223344,1,1000,2000,nullptr,{}};
    mco::WindowDispatchState window{globals,1,Fixture::sync,nullptr,&script};
    mco::MouseInputState mouse{window,image,1,0x7000a000};
    mco::MousePlatformBridge platform{Fixture::convert,Fixture::position,Fixture::cursor,Fixture::notify,&script};
    Sample() {
        script.mouse=&mouse;window.store(input_queue_image::dispatch_synchronizer,1234);
        window.store(input_queue_image::target_window,7);
        mouse.store(mouse_input_image::maximum_x,100);mouse.store(mouse_input_image::maximum_y,80);
    }
};
inline void compare(std::istream& input,unsigned operation) {
    Fixture f{cell_io::read(input),cell_io::read(input),cell_io::read(input),cell_io::read(input),cell_io::read(input)};
    const auto enabled=cell_io::read(input),callback=cell_io::read(input);
    std::array<std::uint32_t,6> args;
    for(auto& v:args)v=cell_io::read(input);
    auto globals=cell_io::image<input_queue_image::size>(input);
    auto image=cell_io::image<mouse_input_image::size>(input);
    mco::WindowDispatchState window{globals,1,f.sync,nullptr,&f};
    mco::MouseInputState mouse{window,image,enabled,callback};f.mouse=&mouse;
    const mco::MousePlatformBridge platform{f.convert,f.position,f.cursor,f.notify,&f};
    std::uint32_t result=0;
    if(operation==0)mco::input_cursor_warp(window,platform,args[0],args[1]);
    else if(operation==1)mco::input_mouse_update(mouse,platform,args[0],args[1],args[2],args[3]);
    else if(operation==2)result=mco::input_mouse_press(mouse,platform,args[0],args[1],args[2],args[3],args[4]);
    else if(operation==3)result=mco::input_mouse_motion(mouse,platform,args[0],args[1],args[2],args[3],args[4]);
    else throw std::invalid_argument("mouse comparison operation");
    cell_io::emit(result);cell_io::emit(mouse.enabled);cell_io::emit(mouse.button_callback);
    cell_io::emit(globals);cell_io::emit(image);cell_io::emit(static_cast<std::uint32_t>(f.logs.size()));
    for(const auto& row:f.logs)cell_io::emit(row);
}
}
