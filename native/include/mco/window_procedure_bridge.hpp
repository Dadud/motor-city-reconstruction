#pragma once
#include "mco/window_dispatch_state.hpp"
namespace mco {
using WindowProcedureInvoke=std::uint32_t (*)(WindowDispatchState&,std::uint32_t handler,
    std::uint32_t owner,std::uint32_t window,std::uint32_t message,std::uint32_t wparam,
    std::uint32_t lparam,std::uint32_t& local_result,void* user);
using WindowDefaultProcedure=std::uint32_t (*)(WindowDispatchState&,std::uint32_t window,
    std::uint32_t message,std::uint32_t wparam,std::uint32_t lparam,void* user);
struct WindowProcedureBridge {
    WindowProcedureInvoke invoke{};
    WindowDefaultProcedure default_procedure{};
    void* user{};
};
}
