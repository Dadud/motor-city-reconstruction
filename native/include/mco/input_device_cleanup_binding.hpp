#pragma once
#include "mco/cleanup_registry.hpp"
#include "mco/input_device_lifetime.hpp"
#include <stdexcept>
namespace mco {
// Connect original registration 0x6bf450 and callback 0x6f0350 to shared state.
struct InputDeviceCleanupBinding {
    CleanupRegistry& registry;
    InputDeviceLifetimeState& device;
    InputDeviceLifetimePlatform previous;
    CleanupRegistryPlatform other_callbacks{};
    static std::uint32_t invoke(InputDeviceLifetimeState& state,std::uint32_t code,std::uint32_t identity,std::span<const std::uint32_t> arguments,std::uint32_t slot,std::uint32_t* output,void* user) {
        auto& self=*static_cast<InputDeviceCleanupBinding*>(user);
        if(code==device_lifetime_call::register_cleanup) {
            if(arguments.size()!=1)throw std::invalid_argument("cleanup registration arguments");
            cleanup_registry_register(self.registry,arguments[0]);return 0;
        }
        if(!self.previous.invoke)throw std::invalid_argument("device lifetime bridge required");
        return self.previous.invoke(state,code,identity,arguments,slot,output,self.previous.user);
    }
    static void cleanup(CleanupRegistry& registry,std::uint32_t identity,void* user) {
        auto& self=*static_cast<InputDeviceCleanupBinding*>(user);
        if(identity==0x6f0350) {input_device_shutdown(self.device,self.platform());return;}
        if(!self.other_callbacks.invoke)throw std::invalid_argument("other cleanup callback bridge required");
        self.other_callbacks.invoke(registry,identity,self.other_callbacks.user);
    }
    InputDeviceLifetimePlatform platform(){return {invoke,this};}
    CleanupRegistryPlatform callbacks(){return {cleanup,this};}
};
}
