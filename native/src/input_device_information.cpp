#include "mco/input_device_information.hpp"
#include "mco/layouts.hpp"
#include "mco/detail/byte_words.hpp"
#include <algorithm>
#include <array>
#include <stdexcept>
namespace mco {
std::uint32_t input_device_information(InputDeviceBridge& device,const InputDeviceInformationBridge& platform,std::span<std::byte,540> output) {
    using detail::read_word;using detail::write_word;
    namespace info=input_device_information_image;
    namespace caps=device_capabilities_record;
    if(!platform.invoke)throw std::invalid_argument("device information virtual-method bridge required");
    std::fill(output.begin(),output.end(),std::byte{});
    // Host initialization makes unread temporary bytes defined; only size tags
    // are original inputs. The bridge populates every subsequently read field.
    std::array<std::byte,device_instance_record::size> instance{};
    std::array<std::byte,caps::size> capabilities{};
    std::array<std::byte,device_object_record::size> object{};
    auto call=[&](std::uint32_t method,std::span<std::byte> record,std::uint32_t selector=0,std::uint32_t flags=0) {
        return platform.invoke(device,device.table,method,record,selector,flags,platform.user);
    };
    write_word(instance,device_instance_record::record_size,static_cast<std::uint32_t>(instance.size()));
    auto status=call(input_device_vtable::device_information,instance);
    if(status!=0)return status;
    write_word(output,info::device_type,read_word(instance,device_instance_record::device_type));
    auto copy_name=[&](std::size_t destination,std::size_t source) {
        bool ended=false;
        for(unsigned i=0;i<259;++i) {
            const auto byte=ended?std::byte{}:instance[source+i];
            output[destination+i]=byte;if(byte==std::byte{})ended=true;
        }
    };
    copy_name(info::instance_name,device_instance_record::instance_name);
    copy_name(info::product_name,device_instance_record::product_name);
    write_word(capabilities,caps::record_size,static_cast<std::uint32_t>(capabilities.size()));
    status=call(input_device_vtable::capabilities,capabilities);
    if(status!=0)return status;
    const auto bits=read_word(capabilities,caps::flags);
    auto previous=read_word(output,info::flags);
    previous=((previous^bits)&1u)^previous;
    write_word(output,info::flags,(((bits>>7)^previous)&2u)^previous);
    write_word(object,device_object_record::record_size,static_cast<std::uint32_t>(object.size()));
    std::uint32_t successes=0;
    for(std::uint32_t index=0;index<32 && successes<read_word(capabilities,caps::buttons);++index) {
        const auto type=read_word(output,info::device_type)&255u;
        if(type==2 || type==4) {
            if(call(input_device_vtable::object_information,object,index+(type==2?12u:48u),1)==0) {
                write_word(output,info::buttons,read_word(output,info::buttons)|(1u<<index));++successes;
            }
        }
    }
    successes=0;
    for(std::uint32_t index=0;index<8 && successes<read_word(capabilities,caps::axes);++index) {
        if(call(input_device_vtable::object_information,object,platform.axis_offsets[index],1)==0) {
            write_word(output,info::axes,read_word(output,info::axes)|(1u<<index));++successes;
        }
    }
    successes=0;
    for(std::uint32_t index=0;index<4 && successes<read_word(capabilities,caps::povs);++index) {
        if(call(input_device_vtable::object_information,object,32+index*4,1)==0) {
            write_word(output,info::povs,read_word(output,info::povs)|(1u<<index));++successes;
        }
    }
    return status;
}
}
