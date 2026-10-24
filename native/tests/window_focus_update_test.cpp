#include "mco/window_focus_update.hpp"
#include <algorithm>
#include <stdexcept>

namespace {
struct Calls {std::uint32_t count{};};
std::uint32_t default_proc(mco::WindowFocusState&,std::uint32_t window,
    std::uint32_t message,std::uint32_t wparam,std::uint32_t lparam,void* user) {
    auto& calls=*static_cast<Calls*>(user);
    ++calls.count;
    return window^message^wparam^lparam;
}
}

int main() {
    using namespace input_queue_image;
    std::array<std::byte,size> globals{};
    std::array<std::byte,4> active{};
    std::array<std::byte,128> keys{};
    mco::detail::write_word(globals,target_window,7);
    mco::detail::write_word(globals,hooks_enabled,0);
    mco::detail::write_word(active,0,0);
    keys.fill(std::byte{0x5a});
    Calls calls{};
    mco::WindowDispatchState dispatch{globals,1,nullptr,nullptr,nullptr};
    mco::WindowFocusState state{dispatch,active,keys,default_proc,
        nullptr,nullptr,nullptr,&calls};
    std::uint32_t result=0;

    if(mco::window_focus_update(state,7,0x86,1,0x1234,result)!=1 ||
       result!=(7u^0x86u^1u^0x1234u) || state.active()!=1 || calls.count!=1)
        throw std::runtime_error("activation did not delegate and set active state");

    if(mco::window_focus_update(state,7,0x86,0,0x1234,result)!=1 ||
       result!=(7u^0x86u^0x1234u) || state.active()!=0 || calls.count!=2 ||
       std::any_of(keys.begin(),keys.end(),[](auto byte){return byte!=std::byte{0};}))
        throw std::runtime_error("deactivation did not clear active and raw-key state");

    result=0xabcdef01;
    if(mco::window_focus_update(state,8,0x86,1,0,result)!=1 ||
       result!=0xabcdef01 || state.active()!=0 || calls.count!=2)
        throw std::runtime_error("foreign window changed focus state");
    return 0;
}
