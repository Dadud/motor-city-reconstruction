#include "mouse_input_cases.hpp"
#include <stdexcept>
int main() {
    mouse_input_cases::Sample f;
    if(mco::input_mouse_motion(f.mouse,f.platform,1,7,0x200,0xffffffff,0xffff8000)!=0 ||
       f.mouse.load(mouse_input_image::buttons)!=7 || f.script.logs.size()!=5 ||
       f.script.logs.back()[0]!=2)
        throw std::runtime_error("motion notified buttons or changed flags");
    f.script.logs.clear();const auto before=f.image;
    if(mco::input_mouse_motion(f.mouse,f.platform,1,8,0x200,1,0)!=0 ||
       f.image!=before || !f.script.logs.empty())
        throw std::runtime_error("wrong-window motion updated state");
}
