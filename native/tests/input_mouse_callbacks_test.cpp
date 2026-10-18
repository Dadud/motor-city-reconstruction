#include "input_mouse_callbacks_cases.hpp"
void require(bool b){if(!b)throw std::runtime_error("mouse callback invariant");}
int main(){
    using namespace mco;
    std::array<std::uint32_t,15> words{};std::uint32_t width=640,height=480;
    InputMouseLifetimeState lifetime{words,width,height};
    std::array<std::byte,input_queue_image::size> globals{};
    std::array<std::byte,mouse_input_image::size> image{};
    WindowDispatchState window{globals,1};window.store(input_queue_image::target_window,7);
    MouseInputState mouse{window,image,0,123};std::uint32_t x=0,y=0,buttons=0,wheel=0,counter=0;
    InputMouseGeometryState geometry{mouse,x,y};std::array<std::uint32_t,3> ids{};
    InputMouseCallbacks s{lifetime,geometry,wheel,counter,buttons,ids};
    input_mouse_driver_setup(s);require(mouse.enabled==1 && mouse.load(mouse_input_image::maximum_x)==640 && ids[2]==0x6f0670);
    require(input_mouse_wheel(s,1,7,0xff880123)==0 && wheel==0xffffff88);
    input_mouse_wheel(s,0,7,120u<<16);input_mouse_wheel(s,1,8,120u<<16);require(wheel==0xffffff88);
    input_mouse_wheel(s,1,7,120u<<16);require(wheel==0);
    input_mouse_counter_decrement(s);require(counter==0xffffffff);input_mouse_counter_increment(s);require(counter==0);
    mouse.store(mouse_input_image::x,31);mouse.store(mouse_input_image::y,37);mouse.store(mouse_input_image::buttons,0x80000000);
    require(input_mouse_report(s)==0x80000000 && x==31 && y==37 && buttons==0x80000000);
    words[13]=1;words[14]=1;input_mouse_shutdown(s,{});require(words[13]==0 && words[14]==1 && mouse.enabled==0);
}
