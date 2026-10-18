#pragma once
#include "mco/startup_initialize.hpp"
#include "mco/input_mouse_runtime_binding.hpp"
namespace mco {
struct StartupMouseBinding {
    InputMouseRuntimeBinding& mouse;
    StartupPlatform previous;
    std::uint32_t temporary;
    static std::uint32_t invoke(StartupState& state,std::uint32_t id,
                               std::span<const std::uint32_t> args,void* user){
        auto& self=*static_cast<StartupMouseBinding*>(user);
        if(id==0x6ef890){
            if(!args.empty())throw std::invalid_argument("startup mouse arguments");
            return input_mouse_lifetime(self.mouse.callbacks.lifetime,
                                        self.mouse.lifetime_platform(),self.temporary);
        }
        if(!self.previous.invoke)throw std::invalid_argument("startup subsystem bridge required");
        return self.previous.invoke(state,id,args,self.previous.user);
    }
    static bool nonempty(std::uint32_t id,void* user){
        auto& self=*static_cast<StartupMouseBinding*>(user);
        if(!self.previous.driver_nonempty)throw std::invalid_argument("startup driver-name view required");
        return self.previous.driver_nonempty(id,self.previous.user);
    }
    StartupPlatform platform(){return {invoke,nonempty,this};}
};
}
