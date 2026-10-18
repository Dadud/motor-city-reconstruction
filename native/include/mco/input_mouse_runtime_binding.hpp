#pragma once
#include "mco/input_mouse_callbacks.hpp"
#include "mco/input_mouse_state_set.hpp"
#include "mco/cleanup_registry.hpp"
#include "mco/window_handler_register.hpp"
namespace mco {
// Shared state binds the original helper identities without copying globals.
struct InputMouseRuntimeBinding {
    InputMouseStateSet& setter;
    InputMouseGeometryState& geometry;
    InputMouseCallbacks& callbacks;
    CleanupRegistry& registry;
    InputMouseLifetimePlatform external;
    InputMouseStateSetPlatform virtual_calls;
    MousePlatformBridge cursor;
    InputMouseGeometryPlatform context;
    static std::uint32_t lifetime_invoke(InputMouseLifetimeState& s,std::uint32_t code,std::uint32_t id,
        std::span<const std::uint32_t> args,std::uint32_t slot,std::span<std::uint32_t> output,void* user){
        auto& b=*static_cast<InputMouseRuntimeBinding*>(user);
        if(code==0x6f06c0){input_mouse_driver_setup(b.callbacks);return 0;}
        if(code==0x6efaf0){if(args.size()!=2)throw std::invalid_argument("mouse setter arguments");return input_mouse_state_set(b.setter,b.state_platform(),args[0],args[1]);}
        if(code==0x6f0720){if(args.size()!=4)throw std::invalid_argument("mouse bounds arguments");input_mouse_set_bounds(b.geometry,b.cursor,args[0],args[1],args[2],args[3]);return 0;}
        if(code==0x6bf450){if(args.size()!=1)throw std::invalid_argument("mouse cleanup registration");cleanup_registry_register(b.registry,args[0]);return 0;}
        if(code==0x582e40){if(args.size()!=2)throw std::invalid_argument("mouse message registration");return window_handler_register(b.geometry.mouse.window,args[0],args[1]);}
        if(code==0x584cf0)return b.geometry.mouse.window.load(input_queue_image::device_window);
        if(!b.external.invoke)throw std::invalid_argument("mouse external platform required");
        return b.external.invoke(s,code,id,args,slot,output,b.external.user);
    }
    static std::uint32_t resolve(InputMouseStateSet& s,std::uint32_t id,void* user){
        auto& b=*static_cast<InputMouseRuntimeBinding*>(user);
        if(!b.virtual_calls.resolve)throw std::invalid_argument("mouse virtual-table resolver required");
        return b.virtual_calls.resolve(s,id,b.virtual_calls.user);
    }
    static std::uint32_t state_invoke(InputMouseStateSet& s,std::uint32_t code,std::uint32_t table,
        std::uint32_t id,std::span<const std::uint32_t> args,void* user){
        auto& b=*static_cast<InputMouseRuntimeBinding*>(user);
        if(code==0x6f07f0){if(args.size()!=2)throw std::invalid_argument("mouse position arguments");input_mouse_set_position(b.geometry,b.cursor,b.context,args[0],args[1]);return 0;}
        if(code==0x584cf0)return b.geometry.mouse.window.load(input_queue_image::device_window);
        if(!b.virtual_calls.invoke)throw std::invalid_argument("mouse virtual platform required");
        return b.virtual_calls.invoke(s,code,table,id,args,b.virtual_calls.user);
    }
    static void cleanup(CleanupRegistry&,std::uint32_t id,void* user){
        auto& b=*static_cast<InputMouseRuntimeBinding*>(user);
        if(id!=0x6efad0)throw std::invalid_argument("unresolved mouse cleanup callback");
        input_mouse_shutdown(b.callbacks,b.lifetime_platform());
    }
    InputMouseLifetimePlatform lifetime_platform(){return {lifetime_invoke,this};}
    InputMouseStateSetPlatform state_platform(){return {resolve,state_invoke,this};}
    CleanupRegistryPlatform cleanup_platform(){return {cleanup,this};}
};
}
