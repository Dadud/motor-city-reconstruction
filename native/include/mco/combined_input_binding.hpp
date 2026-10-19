#pragma once
#include "mco/startup_input_binding.hpp"
#include "mco/startup_mouse_binding.hpp"
#include "mco/startup_toggle_binding.hpp"
#include "mco/input_device_cleanup_binding.hpp"
#include "mco/diagnostic_runtime.hpp"
#include "mco/startup_thread_runtime.hpp"
namespace mco {
// One caller-owned graph for both recovered input devices. References remain
// live: queue, diagnostic words, geometry dimensions and registry are shared.
// The platform owns opaque COM identities; keyboard and mouse need not alias.
struct CombinedInputBinding {
    InputMouseRuntimeBinding& mouse;
    InputDeviceLifetimeState& keyboard;
    InputDeviceLifetimePlatform keyboard_external;
    InputKeyboardLayoutPlatform& layout;
    InputToggleKeyPlatform& toggle;
    StartupPlatform other_startup;
    CleanupRegistryPlatform other_cleanup{};
    std::uint32_t mouse_temporary{},keyboard_temporary{};
    DiagnosticRuntime* diagnostics{};
    DiagnosticPlatform diagnostic_platform{};
    StartupThreadRuntime* thread_runtime{};
    StartupThreadPlatform thread_platform{};
    static std::uint32_t device_call(InputDeviceLifetimeState& state,std::uint32_t code,
        std::uint32_t identity,std::span<const std::uint32_t> args,std::uint32_t slot,
        std::uint32_t* output,void* user){
        auto& b=*static_cast<CombinedInputBinding*>(user);
        if(code==device_lifetime_call::register_cleanup){
            if(args.size()!=1)throw std::invalid_argument("combined cleanup registration");
            cleanup_registry_register(b.mouse.registry,args[0]);return 0;
        }
        if(!b.keyboard_external.invoke)throw std::invalid_argument("combined keyboard platform required");
        return b.keyboard_external.invoke(state,code,identity,args,slot,output,b.keyboard_external.user);
    }
    static std::uint32_t startup(StartupState& state,std::uint32_t id,
        std::span<const std::uint32_t> args,void* user){
        auto& b=*static_cast<CombinedInputBinding*>(user);
        if(id==0x6bedf0 && b.diagnostics){
            if(!args.empty())throw std::invalid_argument("combined diagnostic init arguments");
            diagnostic_initialize(*b.diagnostics,b.diagnostic_platform);return 0;
        }
        if(id==0x6be4f0 && b.thread_runtime){
            if(args.size()!=1)throw std::invalid_argument("combined thread init arguments");
            startup_thread_initialize(*b.thread_runtime,b.mouse.registry,b.thread_platform,args[0]);return 0;
        }
        if(id==0x6ef890){
            if(!args.empty())throw std::invalid_argument("combined mouse init arguments");
            return input_mouse_lifetime(b.mouse.callbacks.lifetime,b.mouse.lifetime_platform(),b.mouse_temporary);
        }
        if(id==0x6bfc80){
            if(!args.empty())throw std::invalid_argument("combined Num Lock arguments");
            input_startup_numlock(b.toggle);
            b.keyboard_temporary=(b.keyboard_temporary&0xffffff00u)|0x45u;return 0;
        }
        if(id==0x6f0200)return input_device_initialize(b.keyboard,b.device_platform(),b.keyboard_temporary);
        if(id==0x6f09f0)return input_keyboard_layout(state.queue,b.layout);
        if(id==0x6f0360){
            if(args.size()!=2)throw std::invalid_argument("combined keyboard setter arguments");
            return input_device_set_state(b.keyboard,b.device_platform(),args[0],args[1]);
        }
        if(!b.other_startup.invoke)throw std::invalid_argument("combined other startup platform required");
        return b.other_startup.invoke(state,id,args,b.other_startup.user);
    }
    static bool nonempty(std::uint32_t id,void* user){
        auto& b=*static_cast<CombinedInputBinding*>(user);
        if(!b.other_startup.driver_nonempty)throw std::invalid_argument("combined driver-name view required");
        return b.other_startup.driver_nonempty(id,b.other_startup.user);
    }
    static void cleanup(CleanupRegistry& registry,std::uint32_t id,void* user){
        auto& b=*static_cast<CombinedInputBinding*>(user);
        if(&registry!=&b.mouse.registry)throw std::invalid_argument("combined registry identity");
        if(id==0x6efad0){input_mouse_shutdown(b.mouse.callbacks,b.mouse.lifetime_platform());return;}
        if(id==0x6f0350){input_device_shutdown(b.keyboard,b.device_platform());return;}
        if(!b.other_cleanup.invoke)throw std::invalid_argument("combined unresolved cleanup callback");
        b.other_cleanup.invoke(registry,id,b.other_cleanup.user);
    }
    InputDeviceLifetimePlatform device_platform(){return {device_call,this};}
    StartupPlatform startup_platform(){return {startup,nonempty,this};}
    CleanupRegistryPlatform cleanup_platform(){return {cleanup,this};}
};
}
