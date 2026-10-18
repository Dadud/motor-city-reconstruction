#include "mco/input_device_state.hpp"
#include "mco/input_device_read.hpp"
#include <stdexcept>
namespace mco {
std::span<const std::byte> input_device_state(InputDeviceAccess& access,std::uint32_t kind) {
    if(kind==2) {
        if(access.enabled!=0) {
            if(!access.get_information)throw std::invalid_argument("device information bridge required");
            if(access.get_information(access,access.device,access.information,access.user)==0)return access.information;
        }
    } else if(kind==6) {
        if(access.enabled!=0) {
            if(!access.resolve)throw std::invalid_argument("device resolver required");
            auto& device=access.resolve(access.device,access.user);
            input_device_read(device,access.keyboard.subspan(direct_key_image::payload),direct_key_image::size-direct_key_image::payload);
            return access.keyboard;
        }
    } else {
        access.diagnostic_file=0x84a0f0;access.diagnostic_line=0x1c1;
        if(!access.invalid_kind)throw std::invalid_argument("invalid device kind diagnostic bridge required");
        access.invalid_kind(access,kind,access.user);
    }
    return {};
}
}
