#include "mco/input_keyboard_layout.hpp"
#include <bit>
#include <stdexcept>
namespace mco {
std::uint32_t input_keyboard_layout(InputKeyQueue& queue,const InputKeyboardLayoutPlatform& platform) {
    // Original loads the IAT function into ESI once for both queries.
    const auto query=platform.query;auto* const user=platform.user;
    if(!query)throw std::invalid_argument("keyboard type bridge required");
    if(query(queue,0,user)!=7)return 0;
    const auto subtype=std::bit_cast<std::int32_t>(query(queue,1,user));
    if(subtype<0xd01 || subtype>0xd04)return 0;
    queue.store(input_queue_image::remap,keyboard_scan_remap_identity);return 1;
}
}
