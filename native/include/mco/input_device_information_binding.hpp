#pragma once
#include "mco/input_device_access.hpp"
#include "mco/input_device_information.hpp"
#include <stdexcept>
#include "mco/layouts.hpp"
namespace mco {
// Bind once for the lifetime of access. Forward keyboard resolution and
// diagnostics through the saved context while replacing information lookup.
struct InputDeviceInformationBinding {
    InputDeviceInformationBridge platform;
    InputDeviceResolve previous_resolve{};
    InputInvalidKind previous_diagnostic{};
    void* previous_user{};
    static InputDeviceBridge& resolve(std::uint32_t identity,void* user){
        auto& binding=*static_cast<InputDeviceInformationBinding*>(user);
        if(!binding.previous_resolve)throw std::invalid_argument("information device resolver required");
        return binding.previous_resolve(identity,binding.previous_user);
    }
    static std::uint32_t information(InputDeviceAccess&,std::uint32_t identity,std::span<std::byte> output,void* user){
        auto& binding=*static_cast<InputDeviceInformationBinding*>(user);
        if(output.size()!=input_device_information_image::size)throw std::invalid_argument("information output view size");
        return input_device_information(resolve(identity,user),binding.platform,std::span<std::byte,540>(output.data(),540));
    }
    static void diagnostic(InputDeviceAccess& access,std::uint32_t kind,void* user){
        auto& binding=*static_cast<InputDeviceInformationBinding*>(user);
        if(!binding.previous_diagnostic)throw std::invalid_argument("information diagnostic bridge required");
        binding.previous_diagnostic(access,kind,binding.previous_user);
    }
    void bind(InputDeviceAccess& access){
        previous_resolve=access.resolve;previous_diagnostic=access.invalid_kind;previous_user=access.user;
        access.resolve=resolve;access.get_information=information;access.invalid_kind=diagnostic;access.user=this;
    }
};
}
