#include "mco/input_callback_dispatch.hpp"
#include <stdexcept>
namespace mco {
std::uint32_t input_callback_fallback(InputCallbackDispatchState& state,const InputCallbackDispatchPlatform& platform){
    if(!platform.available)throw std::invalid_argument("input availability bridge required");
    if(platform.available(state,platform.user)==0)return 0;
    if(!platform.read)throw std::invalid_argument("input read bridge required");
    return platform.read(state,platform.user)&255u;
}
std::uint32_t input_callback_dispatch(InputCallbackDispatchState& state,const InputCallbackDispatchPlatform& platform){
    const auto callback=static_cast<std::uint32_t>(state.callback);
    if(callback!=0 && state.enabled!=0){
        if(!platform.invoke)throw std::invalid_argument("input callback bridge required");
        return platform.invoke(state,callback,platform.user);
    }
    return input_callback_fallback(state,platform);
}
}
