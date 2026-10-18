#include "input_queue_cases.hpp"
#include "mco/free_camera_update.hpp"
#include "mco/window_input_initialize.hpp"
#include "mco/window_message_dispatch.hpp"
#include "mco/window_procedure.hpp"
#include "mco/window_keyboard_binding.hpp"
#include "mco/input_queue_resize.hpp"
struct WindowCameraContext {
    queue_cases::Fixture& fixture;
    mco::InputKeyQueue& queue;
    std::uint32_t creations{};
    std::vector<std::array<std::uint32_t,4>> defaults;
    static void sync(mco::WindowDispatchState&,bool entering,std::uint32_t identity,void* user) {
        auto& context=*static_cast<WindowCameraContext*>(user);
        queue_cases::Fixture::synchronize(context.queue,entering,identity,&context.fixture);
    }
    static std::uint32_t create(mco::WindowDispatchState&,void* user) {
        return 0x12340000u+static_cast<WindowCameraContext*>(user)->creations++*0x100u;
    }
    static std::uint32_t invoke(mco::WindowDispatchState&,std::uint32_t handler,std::uint32_t owner,
        std::uint32_t window,std::uint32_t message,std::uint32_t wparam,std::uint32_t lparam,
        std::uint32_t,void* user) {
        auto& c=*static_cast<WindowCameraContext*>(user);
        return mco::window_keyboard_binding(c.queue,c.fixture.remap,handler,owner,window,message,wparam,lparam);
    }
    static std::uint32_t window_invoke(mco::WindowDispatchState& state,std::uint32_t handler,std::uint32_t owner,
        std::uint32_t window,std::uint32_t message,std::uint32_t wparam,std::uint32_t lparam,
        std::uint32_t&,void* user) {return invoke(state,handler,owner,window,message,wparam,lparam,0,user);}
    static std::uint32_t default_procedure(mco::WindowDispatchState&,std::uint32_t window,std::uint32_t message,
        std::uint32_t wparam,std::uint32_t lparam,void* user) {
        static_cast<WindowCameraContext*>(user)->defaults.push_back({window,message,wparam,lparam});
        return 0xd3f00000u^message;
    }
};
int main() {
    return cell_io::run([](std::istream& input) {
        const auto procedure=cell_io::read(input),system_keys=cell_io::read(input);
        auto image=cell_io::image<512>(input),latches=cell_io::image<512>(input);
        auto subject=cell_io::image<68>(input);
        auto f=queue_cases::Fixture::read(input);auto queue=f.state();
        WindowCameraContext context{f,queue,0,{}};
        mco::WindowDispatchState dispatch{f.globals,1,context.sync,context.invoke,&context,context.create};
        const mco::WindowProcedureBridge bridge{context.window_invoke,context.default_procedure,&context};
        std::array<std::byte,0x6000> arena{};std::array<std::byte,65536> grid{};
        mco::detail::write_word(arena,0x3000+0x680,8);
        const mco::SpatialQueryMemory memory{grid,arena,0x71000000};
        const mco::TrackSurfaceWorld world{memory,{0,0},{1,1},0x71003000,0x71001000,0,8};
        mco::FreeCameraState camera{image,std::span<const std::byte,128>(f.keys.data(),128),latches,
            [](std::uint32_t identity,void* user) -> std::span<const std::byte,68> {
                if(identity!=0x7100b000) throw std::invalid_argument("unmapped camera subject");
                return *static_cast<std::array<std::byte,68>*>(user);
            },&subject};
        const auto count=cell_io::read(input);
        if(count==0 || count>4096) throw std::invalid_argument("window camera lifecycle count");
        for(unsigned i=0;i<count;++i) {
            const auto op=cell_io::read(input),a=cell_io::read(input),b=cell_io::read(input);
            const auto bits=((a&127u)<<16)|((a>>7)<<24)|(b&65535u);
            std::uint32_t result=0;
            if(op==0 || op==1 || op==6 || op==7) {
                const auto message=op==0 ? (system_keys ? 0x104u:0x100u) : op==1 ? (system_keys ? 0x105u:0x101u) : op==7 ? 0x102u:a;
                const auto lparam=op==6 ? 0u : op==7 ? b:bits;
                const auto wparam=op==7 ? a:0x70u;
                result=procedure ? mco::window_procedure(dispatch,bridge,7,message,wparam,lparam) :
                    mco::window_message_dispatch(dispatch,7,message,wparam,lparam,0);
            } else if(op==2) mco::free_camera_update(camera,world,a,b);
            else if(op==3) mco::input_queue_resize(queue,a);
            else if(op==4) result=mco::window_input_initialize(dispatch);
            else if(op==5) dispatch.enabled=a;
            else throw std::invalid_argument("window camera lifecycle operation");
            cell_io::emit(result);cell_io::emit(image);cell_io::emit(latches);f.emit();cell_io::emit(subject);f.logs.clear();
            cell_io::emit(dispatch.enabled);cell_io::emit(context.creations);
            cell_io::emit(static_cast<std::uint32_t>(context.defaults.size()));
            for(const auto& row:context.defaults)cell_io::emit(row);
            context.defaults.clear();
        }
    });
}
