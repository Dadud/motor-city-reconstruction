#include "input_console_cases.hpp"
#include "mco/input_console_dispatch_binding.hpp"
#include "mco/input_callback_dispatch.hpp"
#include <stdexcept>
int main(){
    using mco::detail::write_word;
    auto require=[](bool ok,const char* message){if(!ok)throw std::runtime_error(message);};
    input_console_cases::Fixture f;f.config={0,0x12345678,1,4,1,1,1,0x76543210,1,0,0};auto s=f.state();
    auto reset=[&](){f.logs.clear();f.index=0;s.store(console_input_image::pending,0xffffffff);s.store(console_input_image::handle,0x12345678);};
    reset();s.store(console_input_image::pending,0);
    require(mco::input_console_available(s,f.platform())==1 && mco::input_console_read(s,f.platform())==0 && f.index==0,"zero pending byte not buffered");
    reset();s.store(console_input_image::handle,0xffffffff);
    require(mco::input_console_read(s,f.platform())==0xffffffff && f.logs.size()==2,"invalid handle did not bypass APIs");
    auto event=[](unsigned type,unsigned down,unsigned character,unsigned flags=0){std::array<std::byte,20> r{};r[0]=static_cast<std::byte>(type);mco::detail::write_word(r,4,down);r[12]=std::byte{17};r[14]=static_cast<std::byte>(character);mco::detail::write_word(r,16,flags);return r;};
    reset();f.events={{1,1,event(2,1,0)},{1,1,event(1,0,0)},{1,1,event(1,0x80000000,128)}};
    require(mco::input_console_read(s,f.platform())==128 && f.index==3,"event filtering or ANSI byte changed");
    require(f.logs[f.logs.size()-2][0]==6 && f.logs[f.logs.size()-2][2]==f.config[7],"console mode not restored");
    reset();f.events={{0,1,event(1,1,65)}};f.config[6]=0;
    require(mco::input_console_read(s,f.platform())==0xffffffff && f.logs[f.logs.size()-2][2]==f.config[7],"failed read/get-mode path did not restore supplied mode");
    reset();f.config[6]=1;f.image[30]=std::byte{17};f.image[31]=std::byte{};f.image[32]=std::byte{224};f.image[33]=std::byte{75};f.events={{1,1,event(1,1,0,0x100)}};
    require(mco::input_console_read(s,f.platform())==224 && s.load(console_input_image::pending)==75,"decoded pair not buffered");
    require(mco::input_console_available(s,f.platform())==1 && mco::input_console_read(s,f.platform())==75 && f.index==1,"pending second byte read touched event queue");
    reset();f.config[9]=2;f.events={{1,1,event(1,1,65)}};
    require(mco::input_console_read(s,f.platform())==65 && s.load(console_input_image::pending)==0xabcd,"unlock overwrote saved return");
    f.config[9]=0;reset();s.store(console_input_image::handle,0xfffffffe);f.config[1]=0xffffffff;
    require(mco::input_console_available_unlocked(s,f.platform())==0 && f.logs.size()==1,"availability used failed-open handle");
    reset();s.store(console_input_image::handle,0xfffffffe);
    require(mco::input_console_read_unlocked(s,f.platform())==65 && f.logs[1][1]==0xffffffff,"read added a post-open validity check");
    std::array<std::byte,16> key{};key[8]=std::byte{89};s.store(console_input_image::pending,0x4b00);
    require(mco::input_console_decode(s,key).data()==f.image.data()+console_input_image::pending,"decoder/pending image alias lost");
    s.store(console_input_image::pending,0xffffffff);require(mco::input_console_decode(s,key).empty(),"decoder ignored pending-byte write");
    reset();f.events={{0,1,event(1,1,65)}};mco::InputDeviceCallback callback{};std::uint32_t enabled=0;mco::InputCallbackDispatchState control{callback,enabled};mco::InputConsoleDispatchBinding binding{s,f.platform()};
    require(mco::input_callback_dispatch(control,binding.dispatch())==255,"fallback did not run recovered console bodies or mask EOF");
    reset();f.config[9]=256;auto aliased=event(1,1,0);aliased[12]=std::byte{89};f.events={{1,1,aliased}};
    require(mco::input_console_read(s,f.platform())==0 && s.load(console_input_image::pending)==75,"aliased pair overwritten before first-byte read");
    require(mco::input_console_read(s,f.platform())==75 && f.index==1,"aliased second byte not preserved");
    std::uint32_t marker=0x12345678;binding.previous.invoke=[](mco::InputCallbackDispatchState&,std::uint32_t identity,void* user){return *static_cast<std::uint32_t*>(user)^identity;};binding.previous.user=&marker;
    callback=0x7000e000;enabled=1;const auto calls=f.logs.size();
    require(mco::input_callback_dispatch(control,binding.dispatch())==(marker^0x7000e000u) && f.logs.size()==calls,"console binding lost other callback context");

}
