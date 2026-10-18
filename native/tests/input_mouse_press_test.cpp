#include "mouse_input_cases.hpp"
#include <stdexcept>
int main() {
    mouse_input_cases::Sample f;
    if(mco::input_mouse_press(f.mouse,f.platform,1,7,0x201,0xffffffff,0xffff8000)!=0 ||
       f.mouse.load(mouse_input_image::x)!=100 || f.mouse.load(mouse_input_image::y)!=80 ||
       f.mouse.load(mouse_input_image::buttons)!=7 || f.script.logs.size()!=6 ||
       f.script.logs.back()[0]!=6 || f.script.logs.back()[2]!=7)
        throw std::runtime_error("unsigned packed coordinates or button notification changed");
}
