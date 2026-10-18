#pragma once
#include "mco/input_console_read.hpp"
#include "cell_io.hpp"
#include <algorithm>
#include <string_view>
#include <vector>
namespace input_console_cases {
struct Event {std::uint32_t status,count;std::array<std::byte,20> bytes;};
struct Fixture {
    std::array<std::uint32_t,11> config{};
    std::array<std::byte,2168> image{};
    std::array<std::byte,16> key{};
    std::vector<Event> events;
    unsigned index{};
    std::uint32_t* count_pointer{};
    std::vector<std::array<std::uint32_t,12>> logs;
    void log(mco::InputConsoleState& state,unsigned code,std::uint32_t handle=0,std::uint32_t arg=0,std::array<std::uint32_t,6> extra={}){
        std::array<std::uint32_t,12> row{code,handle,arg,state.load(console_input_image::pending),state.load(console_input_image::handle),index};
        std::copy(extra.begin(),extra.end(),row.begin()+6);logs.push_back(row);
    }
    static Fixture& self(void* user){return *static_cast<Fixture*>(user);}
    static void lock(mco::InputConsoleState& state,bool entering,std::uint32_t identity,void* user){
        auto& f=self(user);if(identity!=8)throw std::invalid_argument("console lock identity");f.log(state,entering?0:1,0,identity);
        if(entering && (f.config[9]&1))state.store(console_input_image::pending,0x1234);
        if(!entering && (f.config[9]&2))state.store(console_input_image::pending,0xabcd);
    }
    static std::uint32_t open(mco::InputConsoleState& state,const mco::InputConsoleOpenOptions& options,void* user){
        auto& f=self(user);if(std::string_view(options.name)!="CONIN$")throw std::invalid_argument("console open name");
        f.log(state,2,1,options.access,{options.share,options.security,options.creation,options.flags,options.template_handle,0});
        if(f.config[9]&4){state.store(console_input_image::handle,0x11223344);state.store(console_input_image::pending,0x7788);}
        return f.config[1];
    }
    static std::uint32_t count(mco::InputConsoleState& state,std::uint32_t handle,std::uint32_t& count,void* user){
        auto& f=self(user);f.log(state,3,handle);f.count_pointer=&count;count=f.config[3];
        if(f.config[9]&8)state.store(console_input_image::handle,0x22334455);return f.config[2];
    }
    static std::uint32_t peek(mco::InputConsoleState& state,std::uint32_t handle,std::span<std::byte> output,std::uint32_t capacity,std::uint32_t& received,void* user){
        auto& f=self(user);f.log(state,4,handle,capacity);std::fill(output.begin(),output.end(),std::byte{});
        for(unsigned i=0;i<std::min<std::size_t>(capacity,f.events.size()-std::min<std::size_t>(f.index,f.events.size()));++i)std::copy(f.events[f.index+i].bytes.begin(),f.events[f.index+i].bytes.end(),output.begin()+i*20);
        received=f.config[5];if(f.config[9]&64)*f.count_pointer=0;return f.config[4];
    }
    static std::uint32_t get_mode(mco::InputConsoleState& state,std::uint32_t handle,std::uint32_t& mode,void* user){
        auto& f=self(user);f.log(state,5,handle);mode=f.config[7];
        if(f.config[9]&16)state.store(console_input_image::handle,0x33445566);return f.config[6];
    }
    static std::uint32_t set_mode(mco::InputConsoleState& state,std::uint32_t handle,std::uint32_t mode,void* user){
        auto& f=self(user);f.log(state,6,handle,mode);
        if(f.config[9]&128)state.store(console_input_image::pending,0x12345678);return f.config[8];
    }
    static std::uint32_t read(mco::InputConsoleState& state,std::uint32_t handle,std::span<std::byte,20> output,std::uint32_t& received,void* user){
        auto& f=self(user);f.log(state,7,handle,1);
        const auto event=f.index<f.events.size()?f.events[f.index]:Event{0,0,{}};++f.index;
        std::copy(event.bytes.begin(),event.bytes.end(),output.begin());received=event.count;
        if(f.config[9]&32){state.store(console_input_image::handle,0x44556677);state.store(console_input_image::pending,0xaabbccdd);}
        if(f.config[9]&256)state.store(console_input_image::pending,0x4b00);
        return event.status;
    }
    mco::InputConsoleState state(){return {image};}
    mco::InputConsolePlatform platform(){return {lock,open,count,peek,get_mode,set_mode,read,this};}
    std::uint32_t run(mco::InputConsoleState& state){
        count_pointer=nullptr;
        switch(config[0]){
        case 0:return mco::input_console_read(state,platform());
        case 1:return mco::input_console_available(state,platform());
        case 2:return mco::input_console_read_unlocked(state,platform());
        case 3:return mco::input_console_available_unlocked(state,platform());
        case 4:{const auto pair=mco::input_console_decode(state,key);return pair.empty()?0u:0x8dc2d0u+static_cast<std::uint32_t>(pair.data()-image.data());}
        case 5:return mco::input_console_open(state,platform());
        default:throw std::invalid_argument("console comparison mode");
        }
    }
    void emit(){cell_io::emit(image);cell_io::emit(index);cell_io::emit(static_cast<std::uint32_t>(logs.size()));for(const auto& row:logs)cell_io::emit(row);}
};
inline void compare(std::istream& input){
    Fixture f;for(auto& v:f.config)v=cell_io::read(input);f.image=cell_io::image<2168>(input);f.key=cell_io::image<16>(input);
    const auto count=cell_io::read(input);if(count>4096)throw std::invalid_argument("console fixture event count");
    for(unsigned i=0;i<count;++i){const auto status=cell_io::read(input),received=cell_io::read(input);f.events.push_back({status,received,cell_io::image<20>(input)});}
    auto state=f.state();cell_io::emit(f.run(state));f.emit();
}
}
