#include "mco/input_default_key.hpp"
#include "mco/input_queue_pop.hpp"
#include <bit>
#include <stdexcept>
namespace mco {
std::uint32_t input_key_action(InputKeyActions& state,std::uint32_t code){
    const auto signed_code=std::bit_cast<std::int32_t>(code);
    std::uint32_t index=0;
    if(signed_code<256){
        const auto offset=static_cast<std::int64_t>(input_action_image::low_map)+signed_code;
        if(offset<0 || offset>=static_cast<std::int64_t>(state.image.size()))throw std::invalid_argument("action map index outside supplied image");
        index=std::to_integer<std::uint32_t>(state.image[static_cast<std::size_t>(offset)]);
    }else if(signed_code<65536){
        index=std::to_integer<std::uint32_t>(state.image[input_action_image::high_map+(code>>8)]);
    }else return code;
    if(index==0)return code;
    const auto handler=detail::read_word(state.image,input_action_image::handlers+index*4);
    if(handler!=0){
        if(!state.invoke)throw std::invalid_argument("key action bridge required");
        state.invoke(state,handler,state.user);
    }
    return 0;
}
std::uint32_t input_default_key(InputDefaultKeyState& state,const InputCallbackDispatchPlatform& platform){
    if(state.control.enabled==0)return input_callback_fallback(state.control,platform);
    return input_key_action(state.actions,input_queue_pop(state.queue,state.translation)&65535u);
}
}
