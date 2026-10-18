#pragma once
#include "mco/input_key_queue.hpp"
namespace mco {
struct WindowDispatchState;
using WindowCreateSync=std::uint32_t (*)(WindowDispatchState&,void* user);
using WindowDispatchSync=void (*)(WindowDispatchState&,bool entering,std::uint32_t identity,void* user);
using WindowDispatchInvoke=std::uint32_t (*)(WindowDispatchState&,std::uint32_t handler,
    std::uint32_t owner,std::uint32_t window,std::uint32_t message,std::uint32_t wparam,
    std::uint32_t lparam,std::uint32_t result_identity,void* user);
struct WindowDispatchState {
    std::span<std::byte,input_queue_image::size> globals;
    std::uint32_t enabled;
    WindowDispatchSync sync{};
    WindowDispatchInvoke invoke{};
    void* user{};
    WindowCreateSync create_sync{};
    std::uint32_t load(std::size_t offset) const {return detail::read_word(globals,offset);}
    void store(std::size_t offset,std::uint32_t value) {detail::write_word(globals,offset,value);}
    void synchronize(bool entering) {
        if(!sync) throw std::invalid_argument("window dispatch synchronization bridge required");
        sync(*this,entering,load(input_queue_image::dispatch_synchronizer),user);
    }
};
}
