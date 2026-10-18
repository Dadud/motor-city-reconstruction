#include "mouse_input_cases.hpp"
#include <stdexcept>
int main() {
    mouse_input_cases::Sample f;f.script.success=0;
    mco::input_cursor_warp(f.window,f.platform,5,6);
    const auto& log=f.script.logs;
    if(log.size()!=3 || log[0][0]!=3 || log[1][0]!=4 || log[1][1]!=5 || log[1][2]!=6 ||
       log[2][0]!=5 || log[2][1]!=0 || f.mouse.load(mouse_input_image::x)!=0)
        throw std::runtime_error("failed conversion fallback or cursor hiding changed");
}
