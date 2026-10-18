#pragma once
#include "mco/input_device_state.hpp"
#include "mco/input_translation_state.hpp"
namespace mco {
struct InputTranslationDeviceBinding {
    InputDeviceAccess& access;
    InputExitRequest exit{};
    void* exit_user{};
    static std::span<const std::byte> get_state(InputTranslationState&,std::uint32_t kind,void* user) {
        return input_device_state(static_cast<InputTranslationDeviceBinding*>(user)->access,kind);
    }
    static void request_exit(InputTranslationState& state,std::uint32_t code,void* user) {
        auto& binding=*static_cast<InputTranslationDeviceBinding*>(user);
        if(!binding.exit)throw std::invalid_argument("device-bound exit bridge required");
        binding.exit(state,code,binding.exit_user);
    }
    void bind(InputTranslationState& state) {
        state.get_state=get_state;state.exit_request=request_exit;state.user=this;
    }
};
}
