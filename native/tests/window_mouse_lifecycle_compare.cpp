#include "mouse_input_cases.hpp"
#include "mco/window_input_initialize.hpp"
#include "mco/window_message_dispatch.hpp"
#include "mco/window_procedure.hpp"
#include "mco/window_mouse_binding.hpp"
namespace {
using Fixture=mouse_input_cases::Fixture;
std::uint32_t create(mco::WindowDispatchState&,void* user) {
    auto& f=*static_cast<Fixture*>(user);f.observe(7);return 0x12340000u+f.creations++*0x100u;
}
std::uint32_t invoke(mco::WindowDispatchState&,std::uint32_t handler,std::uint32_t owner,
    std::uint32_t window,std::uint32_t message,std::uint32_t wparam,std::uint32_t lparam,std::uint32_t,void* user) {
    auto& f=*static_cast<Fixture*>(user);
    return mco::window_mouse_binding(*f.mouse,*f.platform,handler,owner,window,message,wparam,lparam);
}
std::uint32_t window_invoke(mco::WindowDispatchState& state,std::uint32_t handler,std::uint32_t owner,
    std::uint32_t window,std::uint32_t message,std::uint32_t wparam,std::uint32_t lparam,std::uint32_t&,void* user) {
    return invoke(state,handler,owner,window,message,wparam,lparam,0,user);
}
std::uint32_t default_procedure(mco::WindowDispatchState&,std::uint32_t window,std::uint32_t message,
    std::uint32_t wparam,std::uint32_t lparam,void* user) {
    static_cast<Fixture*>(user)->observe(8,window,message,wparam,lparam);return 0xd3f00000u^message;
}
}
int main() {
    return cell_io::run([](std::istream& input) {
        const auto procedure=cell_io::read(input);
        Fixture f{cell_io::read(input),cell_io::read(input),cell_io::read(input),cell_io::read(input),cell_io::read(input)};
        const auto enabled=cell_io::read(input),callback=cell_io::read(input);
        for(unsigned i=0;i<6;++i) cell_io::read(input); // Shared standalone fixture argument slots.
        auto globals=cell_io::image<input_queue_image::size>(input);
        auto image=cell_io::image<mouse_input_image::size>(input);
        mco::WindowDispatchState window{globals,1,Fixture::sync,invoke,&f,create};
        mco::MouseInputState mouse{window,image,enabled,callback};f.mouse=&mouse;
        const mco::MousePlatformBridge platform{Fixture::convert,Fixture::position,Fixture::cursor,Fixture::notify,&f};
        f.platform=&platform;
        const mco::WindowProcedureBridge bridge{window_invoke,default_procedure,&f};
        const auto count=cell_io::read(input);
        if(count==0 || count>4096)throw std::invalid_argument("window mouse lifecycle count");
        for(unsigned i=0;i<count;++i) {
            const auto op=cell_io::read(input),a=cell_io::read(input),b=cell_io::read(input),c=cell_io::read(input);
            std::uint32_t result=0;
            if(op==0)result=mco::window_input_initialize(window);
            else if(op==1)result=procedure ? mco::window_procedure(window,bridge,7,a,b,c):mco::window_message_dispatch(window,7,a,b,c,0);
            else if(op==2)mouse.enabled=a;
            else if(op==3)window.enabled=a;
            else throw std::invalid_argument("window mouse lifecycle operation");
            cell_io::emit(result);cell_io::emit(window.enabled);cell_io::emit(mouse.enabled);cell_io::emit(mouse.button_callback);
            cell_io::emit(f.creations);cell_io::emit(globals);cell_io::emit(image);
            cell_io::emit(static_cast<std::uint32_t>(f.logs.size()));
            for(const auto& row:f.logs)cell_io::emit(row);
            f.logs.clear();
        }
    });
}
