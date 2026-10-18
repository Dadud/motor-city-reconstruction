#include "mouse_input_cases.hpp"
#include <stdexcept>
int main() {
    mouse_input_cases::Sample f;f.mouse.button_callback=0;f.script.mask=64;
    mco::input_mouse_update(f.mouse,f.platform,10,20,0xdeadbeef,1);
    if(f.script.logs.size()!=3 || f.script.logs[0][0]!=1 || f.script.logs[1][0]!=2 ||
       f.script.logs[2][0]!=6 || f.script.logs[2][1]!=0x7000a100 ||
       f.script.logs[2][2]!=0xdeadbeef || f.mouse.enabled!=0)
        throw std::runtime_error("post-leave callback reload or notification argument changed");
    mouse_input_cases::Sample g;g.script.mask=1;
    mco::input_mouse_update(g.mouse,g.platform,101,81,7,0);
    if(g.mouse.load(mouse_input_image::x)!=100 || g.mouse.load(mouse_input_image::y)!=80)
        throw std::runtime_error("coordinates were reclamped after entering");
    g.script.logs.clear();g.mouse.enabled=0;
    mco::input_mouse_update(g.mouse,{},0,0,0,1);
    if(!g.script.logs.empty()) throw std::runtime_error("disabled mouse invoked bridge");
}
