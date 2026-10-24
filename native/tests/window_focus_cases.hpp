#pragma once
#include "cell_io.hpp"
#include "mco/window_focus_update.hpp"
#include <array>
#include <vector>

namespace window_focus_cases {
using Row=std::array<std::uint32_t,11>;
struct Fixture {
    std::uint32_t module,default_result,keyboard_result,mouse_result;
    std::uint32_t set_count{};
    mco::WindowFocusState* state{};
    std::vector<Row> calls;
    Row snapshot(std::uint32_t kind,std::uint32_t a,std::uint32_t b,
                 std::uint32_t c,std::uint32_t d,std::uint32_t result) const {
        return {kind,a,b,c,d,result,state->active(),
            state->keyboard_hook(),state->mouse_hook(),
            std::to_integer<std::uint32_t>(state->raw_keys[0]),
            std::to_integer<std::uint32_t>(state->raw_keys[127])};
    }
    static std::uint32_t default_proc(mco::WindowFocusState& s,std::uint32_t window,
        std::uint32_t message,std::uint32_t wparam,std::uint32_t lparam,void* user) {
        auto& f=*static_cast<Fixture*>(user);
        f.calls.push_back(f.snapshot(0,window,message,wparam,lparam,f.default_result));
        return f.default_result;
    }
    static std::uint32_t unhook(mco::WindowFocusState& s,std::uint32_t hook,void* user) {
        auto& f=*static_cast<Fixture*>(user);
        f.calls.push_back(f.snapshot(1,hook,0,0,0,1)); return 1;
    }
    static std::uint32_t get_module(mco::WindowFocusState& s,void* user) {
        auto& f=*static_cast<Fixture*>(user);
        f.calls.push_back(f.snapshot(2,0,0,0,0,f.module)); return f.module;
    }
    static std::uint32_t set_hook(mco::WindowFocusState& s,std::uint32_t id,
        std::uint32_t callback,std::uint32_t module,std::uint32_t thread,void* user) {
        auto& f=*static_cast<Fixture*>(user);
        const auto result=f.set_count++==0 ? f.keyboard_result : f.mouse_result;
        f.calls.push_back(f.snapshot(3,id,callback,module,thread,result)); return result;
    }
};

inline void compare(std::istream& input) {
    using namespace cell_io;
    const auto enabled=read(input),window=read(input),message=read(input),
        wparam=read(input),lparam=read(input),old_result=read(input),
        module=read(input),default_result=read(input),keyboard_result=read(input),
        mouse_result=read(input);
    auto globals=image<input_queue_image::size>(input);
    auto active=image<4>(input);
    auto keys=image<128>(input);
    mco::WindowDispatchState dispatch{globals,enabled,nullptr,nullptr,nullptr};
    Fixture f{module,default_result,keyboard_result,mouse_result};
    mco::WindowFocusState state{dispatch,active,keys,Fixture::default_proc,
        Fixture::unhook,Fixture::get_module,Fixture::set_hook,&f};
    f.state=&state;
    auto result=old_result;
    const auto returned=mco::window_focus_update(state,window,message,wparam,lparam,result);
    emit(returned);emit(result);emit(globals);emit(active);emit(keys);
    emit(static_cast<std::uint32_t>(f.calls.size()));
    for(const auto& row:f.calls) emit(row);
}
}
