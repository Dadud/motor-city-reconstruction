#include "mco/input_console_read.hpp"
#include <array>
#include <limits>
#include <stdexcept>
#include <vector>
namespace mco {
namespace {
std::uint32_t half(std::span<const std::byte> image,std::size_t offset){return std::to_integer<std::uint32_t>(image[offset])|(std::to_integer<std::uint32_t>(image[offset+1])<<8);}
void lock(InputConsoleState& state,const InputConsolePlatform& platform,bool entering){if(!platform.lock)throw std::invalid_argument("console lock bridge required");platform.lock(state,entering,8,platform.user);}
}
std::uint32_t input_console_open(InputConsoleState& state,const InputConsolePlatform& platform){
    if(!platform.open)throw std::invalid_argument("console open bridge required");
    const auto handle=platform.open(state,{"CONIN$",0xc0000000,3,0,3,0,0},platform.user);
    state.store(console_input_image::handle,handle);return handle;
}
std::span<const std::byte> input_console_decode(InputConsoleState& state,std::span<const std::byte,console_key_record::size> key){
    const auto flags=detail::read_word(key,console_key_record::control),scan=half(key,console_key_record::scan);
    const auto plane=(flags&3)?6u:(flags&12)?4u:(flags&16)?2u:0u;
    if(flags&0x100){
        for(unsigned row=0;row<12;++row){const auto at=console_input_image::enhanced_rows+row*10;if(half(state.image,at)==scan)return state.image.subspan(at+2+plane,2);}
        return {};
    }
    if(scan>255)throw std::invalid_argument("normal console scan outside supplied window");
    const auto pair=state.image.subspan(console_input_image::normal_rows+scan*8+plane,2);
    if((pair[0]!=std::byte{} && pair[0]!=std::byte{224}) || pair[1]==std::byte{})return {};
    return pair;
}
std::uint32_t input_console_available_unlocked(InputConsoleState& state,const InputConsolePlatform& platform){
    if(state.load(console_input_image::pending)!=0xffffffff)return 1;
    if(state.load(console_input_image::handle)==0xfffffffe)input_console_open(state,platform);
    if(state.load(console_input_image::handle)==0xffffffff)return 0;
    if(!platform.count)throw std::invalid_argument("console event count bridge required");
    std::uint32_t count=0;
    if(platform.count(state,state.load(console_input_image::handle),count,platform.user)==0 || count==0)return 0;
    if(count>std::numeric_limits<std::uint32_t>::max()/console_event_record::size)throw std::invalid_argument("console allocation exceeds original bounded domain");
    const auto capacity=count;std::vector<std::byte> records(static_cast<std::size_t>(capacity)*console_event_record::size);
    if(!platform.peek)throw std::invalid_argument("console peek bridge required");
    std::uint32_t received=0;
    if(platform.peek(state,state.load(console_input_image::handle),records,capacity,received,platform.user)==0 || received==0 || received>count)return 0;
    if(received>capacity)throw std::invalid_argument("console peek outside allocated view");
    for(unsigned i=0;i<received;++i){
        const auto record=std::span<const std::byte>(records).subspan(i*console_event_record::size,console_event_record::size);
        if(half(record,console_event_record::event_type)!=1)continue;
        const auto key=std::span<const std::byte,console_key_record::size>(record.data()+console_event_record::key_event,console_key_record::size);
        if(detail::read_word(key,console_key_record::key_down)==0)continue;
        if(key[console_key_record::character]!=std::byte{} || !input_console_decode(state,key).empty())return 1;
    }
    return 0;
}
std::uint32_t input_console_read_unlocked(InputConsoleState& state,const InputConsolePlatform& platform){
    const auto pending=state.load(console_input_image::pending);
    if(pending!=0xffffffff){state.store(console_input_image::pending,0xffffffff);return pending&255u;}
    if(state.load(console_input_image::handle)==0xffffffff)return 0xffffffff;
    if(state.load(console_input_image::handle)==0xfffffffe)input_console_open(state,platform);
    if(!platform.get_mode || !platform.set_mode || !platform.read)throw std::invalid_argument("console read/mode bridges required");
    std::uint32_t saved_mode=0;platform.get_mode(state,state.load(console_input_image::handle),saved_mode,platform.user);
    platform.set_mode(state,state.load(console_input_image::handle),0,platform.user);
    std::array<std::byte,console_event_record::size> record{};std::uint32_t result=0xffffffff;
    for(;;){
        std::uint32_t received=0;
        if(platform.read(state,state.load(console_input_image::handle),record,received,platform.user)==0 || received==0)break;
        if(half(record,console_event_record::event_type)!=1)continue;
        const auto key=std::span<const std::byte,console_key_record::size>(record.data()+console_event_record::key_event,console_key_record::size);
        if(detail::read_word(key,console_key_record::key_down)==0)continue;
        if(key[console_key_record::character]!=std::byte{}){result=std::to_integer<std::uint32_t>(key[console_key_record::character]);break;}
        const auto pair=input_console_decode(state,key);
        if(!pair.empty()){result=std::to_integer<std::uint32_t>(pair[0]);const auto second=std::to_integer<std::uint32_t>(pair[1]);state.store(console_input_image::pending,second);break;}
    }
    platform.set_mode(state,state.load(console_input_image::handle),saved_mode,platform.user);return result;
}
std::uint32_t input_console_read(InputConsoleState& state,const InputConsolePlatform& platform){lock(state,platform,true);const auto result=input_console_read_unlocked(state,platform);lock(state,platform,false);return result;}
std::uint32_t input_console_available(InputConsoleState& state,const InputConsolePlatform& platform){lock(state,platform,true);const auto result=input_console_available_unlocked(state,platform);lock(state,platform,false);return result;}
}
