#include "mco/input_toggle_key.hpp"
#include <stdexcept>
namespace mco {
void input_toggle_key(std::uint32_t selector, std::uint32_t desired,
                      const InputToggleKeyPlatform& platform) {
    std::uint32_t key, scan, down=0, up=2;
    switch(selector) {
    case 0: key=0x14;scan=0x3a;break;
    case 1: key=0x90;scan=0x45;down=1;up=3;break;
    case 2: key=0x91;scan=0x46;break;
    default:return;
    }
    if(!platform.query)throw std::invalid_argument("toggle-key query bridge required");
    if((platform.query(key,platform.user)&1)!=desired) {
        // The event import is read after the query, then cached for both events.
        const auto event=platform.event;auto* const user=platform.user;
        if(!event)throw std::invalid_argument("toggle-key event bridge required");
        event(key,scan,down,0,user);
        event(key,scan,up,0,user);
    }
}
void input_startup_numlock(const InputToggleKeyPlatform& platform) {
    input_toggle_key(1,0,platform);
}
}
