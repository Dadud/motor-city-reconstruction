#pragma once
#include "mco/input_default_key.hpp"
#include <stdexcept>
namespace mco {
struct InputDefaultKeyBinding {
    InputDefaultKeyState& key;
    InputCallbackDispatchPlatform previous;
    static std::uint32_t available(InputCallbackDispatchState& state,void* user){
        auto& binding=*static_cast<InputDefaultKeyBinding*>(user);
        if(!binding.previous.available)throw std::invalid_argument("default key availability bridge required");
        return binding.previous.available(state,binding.previous.user);
    }
    static std::uint32_t read(InputCallbackDispatchState& state,void* user){
        auto& binding=*static_cast<InputDefaultKeyBinding*>(user);
        if(!binding.previous.read)throw std::invalid_argument("default key read bridge required");
        return binding.previous.read(state,binding.previous.user);
    }
    static std::uint32_t invoke(InputCallbackDispatchState& state,std::uint32_t identity,void* user){
        auto& binding=*static_cast<InputDefaultKeyBinding*>(user);
        if(identity==0x6f0580)return input_default_key(binding.key,binding.previous);
        if(!binding.previous.invoke)throw std::invalid_argument("other key callback bridge required");
        return binding.previous.invoke(state,identity,binding.previous.user);
    }
    InputCallbackDispatchPlatform platform(){return {available,read,invoke,this};}
};
}
