#pragma once
#include "mco/startup_initialize.hpp"
#include "mco/input_device_lifetime.hpp"
#include "mco/input_keyboard_layout.hpp"
namespace mco {
struct StartupInputBinding {
    InputDeviceLifetimeState& device;
    InputDeviceLifetimePlatform device_platform;
    InputKeyboardLayoutPlatform& layout_platform;
    StartupPlatform previous;
    std::uint32_t incoming_temporary;
    static std::uint32_t invoke(StartupState& state,std::uint32_t id,std::span<const std::uint32_t> args,void* user){
        auto& self=*static_cast<StartupInputBinding*>(user);
        if(id==0x6f0200)return input_device_initialize(self.device,self.device_platform,self.incoming_temporary);
        if(id==0x6f09f0)return input_keyboard_layout(state.queue,self.layout_platform);
        if(id==0x6f0360){if(args.size()!=2)throw std::invalid_argument("startup input setter arguments");return input_device_set_state(self.device,self.device_platform,args[0],args[1]);}
        if(!self.previous.invoke)throw std::invalid_argument("startup subsystem bridge required");
        return self.previous.invoke(state,id,args,self.previous.user);
    }
    static bool nonempty(std::uint32_t id,void* user){
        auto& self=*static_cast<StartupInputBinding*>(user);
        if(!self.previous.driver_nonempty)throw std::invalid_argument("startup driver-name view required");
        return self.previous.driver_nonempty(id,self.previous.user);
    }
    StartupPlatform platform(){return {invoke,nonempty,this};}
};
}
