#pragma once
#include "mco/input_console_read.hpp"
#include "mco/input_callback_dispatch_state.hpp"
#include <stdexcept>
namespace mco {
struct InputConsoleDispatchBinding {
    InputConsoleState& console;
    InputConsolePlatform platform;
    InputCallbackDispatchPlatform previous{};
    static std::uint32_t available(InputCallbackDispatchState&,void* user){auto& b=*static_cast<InputConsoleDispatchBinding*>(user);return input_console_available(b.console,b.platform);}
    static std::uint32_t read(InputCallbackDispatchState&,void* user){auto& b=*static_cast<InputConsoleDispatchBinding*>(user);return input_console_read(b.console,b.platform);}
    static std::uint32_t invoke(InputCallbackDispatchState& state,std::uint32_t identity,void* user){
        auto& b=*static_cast<InputConsoleDispatchBinding*>(user);
        if(!b.previous.invoke)throw std::invalid_argument("console callback forward bridge required");
        return b.previous.invoke(state,identity,b.previous.user);
    }
    InputCallbackDispatchPlatform dispatch(){return {available,read,invoke,this};}
};
}
