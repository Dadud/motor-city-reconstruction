#include "mco/input_device_lifetime.hpp"
#include "mco/input_queue_resize.hpp"
#include "mco/layouts.hpp"
#include <initializer_list>
#include <stdexcept>
namespace mco {
namespace {
std::uint32_t call(InputDeviceLifetimeState& state,const InputDeviceLifetimePlatform& platform,std::uint32_t code,std::uint32_t identity=0,std::initializer_list<std::uint32_t> args={},std::uint32_t slot=0,std::uint32_t* output=nullptr){
    if(!platform.invoke)throw std::invalid_argument("device lifetime platform bridge required");
    return platform.invoke(state,code,identity,{args.begin(),args.size()},slot,output,platform.user);
}
}
// Original 0x6f0310.
void input_device_cleanup(InputDeviceLifetimeState& state,const InputDeviceLifetimePlatform& platform){
    using namespace device_lifetime_call;
    if(state.device!=0){
        call(state,platform,unacquire,state.device);
        call(state,platform,release,state.device);
        state.device=0;
    }
    if(state.interface_handle!=0){
        call(state,platform,release,state.interface_handle);
        state.interface_handle=0;
    }
}
// Original registered callback 0x6f0350, absent from retained static enumeration.
void input_device_shutdown(InputDeviceLifetimeState& state,const InputDeviceLifetimePlatform& platform){
    input_device_cleanup(state,platform);state.initialized=0;
}
// Original 0x6f0360.
std::uint32_t input_device_set_state(InputDeviceLifetimeState& state,const InputDeviceLifetimePlatform& platform,std::uint32_t kind,std::uint32_t value){
    if(kind==0){input_queue_resize(state.queue,value);return 1;}
    if(kind==10){state.callback=value;return 1;}
    state.diagnostic_file=0x84a0f0;state.diagnostic_line=0x117;
    call(state,platform,device_lifetime_call::diagnostic,0,{0x84a0fc});return 0;
}
// Original 0x584cf0.
std::uint32_t input_device_window(InputKeyQueue& queue){return queue.load(input_queue_image::device_window);}
std::uint32_t input_device_initialize(InputDeviceLifetimeState& state,const InputDeviceLifetimePlatform& platform,std::uint32_t temporary){
    using namespace device_lifetime_call;
    if(state.initialized==0){
        state.initialized=1;state.queue.store(input_queue_image::raw_mode,0);
        if(state.queue.load(input_queue_image::dispatch_synchronizer)==0){
            const auto sync=call(state,platform,create_sync);state.queue.store(input_queue_image::dispatch_synchronizer,sync);
        }
        input_device_set_state(state,platform,0,32);
    }
    if(state.interface_handle==0){
        const auto module=call(state,platform,module_handle,0,{0});
        auto status=call(state,platform,create_input,0,{module,0x500,0},1,&state.interface_handle);
        if(status==0){
            status=call(state,platform,create_device,state.interface_handle,{0x84c940,0},2,&temporary);
            if(status==0){
                status=call(state,platform,query,temporary,{0x84ca70},3,&state.device);
                call(state,platform,release,temporary);
                if(status==0){
                    status=call(state,platform,set_format,state.device,{0x84b738});
                    if(status==0){
                        const auto window=input_device_window(state.queue);
                        status=call(state,platform,set_cooperative,state.device,{window,6});
                    }
                }
            }
        }
        if(status!=0)input_device_cleanup(state,platform);
    }
    if(state.cleanup_registered==0){
        call(state,platform,register_cleanup,0,{0x6f0350});state.cleanup_registered=1;
    }
    return state.initialized;
}
}
