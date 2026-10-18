#pragma once
#include "cell_io.hpp"
#include "mco/window_message_dispatch.hpp"
#include "mco/window_procedure.hpp"
#include <vector>
namespace window_dispatch_cases {
struct Fixture {
    std::uint32_t mask,value,retval,message;
    std::array<std::byte,4> result;
    std::vector<std::array<std::uint32_t,8>> logs;
    std::uint32_t* local_result{};
    std::uint32_t creation_stride{},creation_calls{};
    static void sync(mco::WindowDispatchState& state,bool entering,std::uint32_t identity,void* user) {
        auto& f=*static_cast<Fixture*>(user);
        using namespace input_queue_image;
        f.logs.push_back({entering?1u:2u,identity,state.enabled,state.load(message_handler_count),
                         state.load(dispatch_synchronizer),state.load(message_handlers),state.load(message_handlers+4),0});
        if(entering) {
            if(f.mask&1) state.enabled=0;
            if(f.mask&2) {state.store(message_handler_count,1);state.store(message_handlers,f.message);state.store(message_handlers+4,0x70009100);}
            if(f.mask&4) state.store(dispatch_synchronizer,state.load(dispatch_synchronizer)^f.value);
            if(f.mask&8) state.store(message_handler_count,0);
        } else {
            if(f.mask&32) state.enabled^=1;
            if((f.mask&128) && f.local_result) *f.local_result=f.value^0x55aa55aau;
        }
    }
    static std::uint32_t invoke(mco::WindowDispatchState& state,std::uint32_t handler,std::uint32_t owner,
        std::uint32_t window,std::uint32_t message,std::uint32_t wparam,std::uint32_t lparam,
        std::uint32_t result_identity,void* user) {
        auto& f=*static_cast<Fixture*>(user);
        if(handler!=0x70009000 && handler!=0x70009100) throw std::invalid_argument("unmapped window handler");
        f.logs.push_back({3,handler,owner,window,message,wparam,lparam,result_identity});
        if(f.mask&16) state.store(input_queue_image::dispatch_synchronizer,
            state.load(input_queue_image::dispatch_synchronizer)^f.value^0x11223344u);
        if((f.mask&64) && result_identity) {
            if(result_identity!=0x71003000) throw std::invalid_argument("unmapped result identity");
            mco::detail::write_word(f.result,0,f.value);
        }
        return f.retval+(handler==0x70009100 ? 1u : 0u);
    }
    static std::uint32_t window_invoke(mco::WindowDispatchState& state,std::uint32_t handler,std::uint32_t owner,
        std::uint32_t window,std::uint32_t message,std::uint32_t wparam,std::uint32_t lparam,
        std::uint32_t& result,void* user) {
        auto& f=*static_cast<Fixture*>(user);
        f.local_result=&result;
        // The observed slot is initialized to zero; its stack address is not a host identity.
        const auto handled=invoke(state,handler,owner,window,message,wparam,lparam,0,user);
        if(f.mask&64) result=f.value;
        return handled;
    }
    static std::uint32_t default_procedure(mco::WindowDispatchState& state,std::uint32_t window,
        std::uint32_t message,std::uint32_t wparam,std::uint32_t lparam,void* user) {
        auto& f=*static_cast<Fixture*>(user);
        f.logs.push_back({4,window,message,wparam,lparam,state.enabled,
                         state.load(input_queue_image::message_handler_count),state.load(input_queue_image::dispatch_synchronizer)});
        if(f.mask&256) state.enabled=0;
        return f.value^0x87654321u;
    }
};
inline void compare(std::istream& input,bool procedure=false) {
    const auto enabled=cell_io::read(input),mask=cell_io::read(input),value=cell_io::read(input),retval=cell_io::read(input);
    const auto window=cell_io::read(input),message=cell_io::read(input),wparam=cell_io::read(input),lparam=cell_io::read(input);
    const auto result_identity=cell_io::read(input);
    auto globals=cell_io::image<input_queue_image::size>(input);
    Fixture f{mask,value,retval,message,cell_io::image<4>(input),{}};
    mco::WindowDispatchState state{globals,enabled,Fixture::sync,Fixture::invoke,&f};
    if(procedure) {
        const mco::WindowProcedureBridge bridge{Fixture::window_invoke,Fixture::default_procedure,&f};
        cell_io::emit(mco::window_procedure(state,bridge,window,message,wparam,lparam));
    } else cell_io::emit(mco::window_message_dispatch(state,window,message,wparam,lparam,result_identity));
    cell_io::emit(state.enabled);cell_io::emit(globals);cell_io::emit(f.result);
    cell_io::emit(static_cast<std::uint32_t>(f.logs.size()));
    for(const auto& row:f.logs)cell_io::emit(row);
}
}
