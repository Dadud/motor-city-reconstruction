#include "mco/input_device_read.hpp"
#include <algorithm>
#include "mco/layouts.hpp"
#include <stdexcept>
namespace mco {
namespace {
constexpr std::uint32_t acquire_method=input_device_vtable::acquire,read_method=input_device_vtable::read_state,poll_method=input_device_vtable::poll;
bool recoverable(std::uint32_t status) {return status==0x8007000cu || status==0x8007001eu;}
std::uint32_t invoke(InputDeviceBridge& device,std::uint32_t method,std::span<std::byte> destination={},std::uint32_t size=0) {
    if(!device.invoke)throw std::invalid_argument("device virtual-method bridge required");
    return device.invoke(device,device.table,method,destination,size,device.user);
}
}
std::uint32_t input_device_poll(InputDeviceBridge& device) {
    auto status=invoke(device,poll_method);
    if(recoverable(status)) {
        status=invoke(device,acquire_method);
        if(status==0)status=invoke(device,poll_method);
    }
    return status;
}
std::uint32_t input_device_read_retry(InputDeviceBridge& device,std::span<std::byte> destination,std::uint32_t size) {
    if(size>destination.size())throw std::invalid_argument("device output view too small");
    auto status=invoke(device,read_method,destination,size);
    if(recoverable(status)) {
        status=invoke(device,acquire_method);
        if(status==0)status=invoke(device,read_method,destination,size);
    }
    return status;
}
std::uint32_t input_device_read(InputDeviceBridge& device,std::span<std::byte> destination,std::uint32_t size) {
    input_device_poll(device);
    const auto status=input_device_read_retry(device,destination,size);
    if(status!=0)std::fill_n(destination.begin(),size,std::byte{});
    return status;
}
}
