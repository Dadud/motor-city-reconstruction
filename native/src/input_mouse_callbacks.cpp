#include "mco/input_mouse_callbacks.hpp"
namespace mco {
void input_mouse_driver_setup(InputMouseCallbacks& s){
    auto& m=s.geometry.mouse;const auto width=s.lifetime.width,height=s.lifetime.height;
    m.store(mouse_input_image::maximum_x,width);m.store(mouse_input_image::minimum_x,0);
    m.store(mouse_input_image::minimum_y,0);s.counter=0;
    m.store(mouse_input_image::maximum_y,height);m.enabled=1;
    s.callback_ids={0x6f06b0,0x6f06a0,0x6f0670};
}
std::uint32_t input_mouse_wheel(InputMouseCallbacks& s,std::uint32_t enabled,
                                std::uint32_t window,std::uint32_t wparam){
    if(enabled && window==s.geometry.mouse.window.load(input_queue_image::target_window)){
        auto delta=wparam>>16;if(delta&0x8000)delta|=0xffff0000;
        s.wheel+=delta;
    }
    return 0;
}
void input_mouse_shutdown(InputMouseCallbacks& s,const InputMouseLifetimePlatform& platform){
    input_mouse_cleanup(s.lifetime,platform);s.lifetime.words[13]=0;s.geometry.mouse.enabled=0;
}
std::uint32_t input_mouse_report(InputMouseCallbacks& s){
    auto& m=s.geometry.mouse;const auto x=m.load(mouse_input_image::x),y=m.load(mouse_input_image::y),buttons=m.load(mouse_input_image::buttons);
    s.geometry.position_x=x;s.geometry.position_y=y;s.reported_buttons=buttons;return buttons;
}
void input_mouse_counter_increment(InputMouseCallbacks& s){++s.counter;}
void input_mouse_counter_decrement(InputMouseCallbacks& s){--s.counter;}
}
