#include "input_mouse_runtime_cases.hpp"
#include "startup_initialize_cases.hpp"
#include "mco/startup_mouse_binding.hpp"
#include "mco/startup_toggle_binding.hpp"
#include "input_toggle_key_cases.hpp"
namespace {
using namespace mco;
using Backend=input_mouse_runtime_cases::Fixture;
struct Fixture {
    Backend mouse;
    StartupState* startup{};
    StartupPlatform previous{};
    static std::uint32_t resolve(InputMouseStateSet& s,std::uint32_t id,void* u){
        return Backend::resolve(s,id,&static_cast<Fixture*>(u)->mouse);
    }
    static std::uint32_t state(InputMouseStateSet& s,std::uint32_t code,std::uint32_t table,
                               std::uint32_t id,std::span<const std::uint32_t> args,void* u){
        auto& f=*static_cast<Fixture*>(u);
        if(code==startup_initialize_cases::diag0 || code==startup_initialize_cases::diag1)
            return f.previous.invoke(*f.startup,code,args,f.previous.user);
        return Backend::state_call(s,code,table,id,args,&f.mouse);
    }
};
}
int main(){return cell_io::run([](std::istream& input){
    Fixture f;auto& backend=f.mouse;
    const auto profile=cell_io::read(input),script=cell_io::read(input),seed=cell_io::read(input),variant=cell_io::read(input);
    if(variant>3)throw std::invalid_argument("startup mouse variant");
    backend.backend.config={0,profile,script,seed};
    for(unsigned i=0;i<6;++i)backend.backend.tables[i]=(seed+i)%2;
    startup_initialize_cases::Fixture startup;
    for(auto& v:startup.config)v=cell_io::read(input);
    for(auto& v:startup.values)v=cell_io::read(input);
    std::array<std::byte,input_queue_image::size> globals{};
    std::array<std::byte,256> keys{};
    InputKeyQueue queue{globals,keys,nullptr,nullptr};
    StartupState state{queue,startup.values};using G=StartupGlobal;
    std::array<std::uint32_t,15> words{};
    InputMouseLifetimeState lifetime{words,state.at(G::width),state.at(G::height)};
    std::array<std::byte,mouse_input_image::size> image{};
    WindowDispatchState window{globals,1,Backend::sync,Backend::dispatch,&backend};
    window.store(input_queue_image::target_window,7);window.store(input_queue_image::device_window,7);
    window.store(input_queue_image::dispatch_synchronizer,0x12345678);
    MouseInputState mouse{window,image,0,0};
    std::uint32_t x=0,y=0,buttons=0,wheel=0,counter=0,mode=0,state8=0,state9=0;
    std::array<std::uint32_t,3> ids{};
    InputMouseGeometryState geometry{mouse,x,y};
    InputMouseCallbacks callbacks{lifetime,geometry,wheel,counter,buttons,ids};
    InputMouseStateSet setter{lifetime,mode,state8,state9,state.at(G::diagnostic_callback),
                             state.at(G::diagnostic_file),state.at(G::diagnostic_line)};
    std::array<std::uint32_t,64> slots{};
    if(variant==3)slots.fill(0x6efad0);
    CleanupRegistry registry{slots};
    InputMouseRuntimeBinding runtime{setter,geometry,callbacks,registry,{Backend::external,&backend},
        {Fixture::resolve,Fixture::state,&f},
        {Backend::convert,Backend::position,Backend::cursor,nullptr,&backend},{Backend::context,&backend}};
    backend.binding=&runtime;f.startup=&state;f.previous=startup.platform();
    StartupMouseBinding binding{runtime,startup.platform(),0x71001400};
    input_toggle_key_cases::Calls toggle;
    constexpr std::array<std::uint32_t,4> key_states{0,1,0xffff,0x8000};
    toggle.state=key_states[variant];toggle.script=(seed&3)|4;
    // Keyboard initialization is a declared boundary in this probe; the word
    // contract is observed by the separate startup/device/Num Lock probe.
    std::uint32_t incoming_word=0;
    StartupToggleBinding combined{toggle.platform,incoming_word,binding.platform()};
    const auto count=cell_io::read(input);
    if(count==0 || count>256)throw std::invalid_argument("startup mouse step count");
    for(unsigned i=0;i<count;++i){
        const auto op=cell_io::read(input),a=cell_io::read(input),b=cell_io::read(input),c=cell_io::read(input);(void)c;
        std::uint32_t result=0;
        switch(op){
        case 0:startup_initialize(state,combined.platform());break;
        case 1:result=input_mouse_state_set(setter,runtime.state_platform(),a,b);break;
        case 2:result=window_message_dispatch(window,b,0x20a,a,0,0);break;
        case 3:cleanup_registry_run(registry,runtime.cleanup_platform());break;
        case 4:state.at(G::width)=a;state.at(G::height)=b;break;
        case 5:state.at(G::graphics_ready)=a;break;
        case 6:{const std::array<std::uint32_t,6> args{0,0,0,a,b,500};input_mouse_bounds(lifetime,runtime.lifetime_platform(),args);break;}
        case 7:input_mouse_set_position(geometry,runtime.cursor,runtime.context,a,b);break;
        case 8:cleanup_registry_register(registry,0x6efad0);break;
        case 9:result=input_mouse_report(callbacks);break;
        case 10:input_mouse_counter_increment(callbacks);break;
        case 11:input_mouse_counter_decrement(callbacks);break;
        default:throw std::invalid_argument("startup mouse operation");
        }
        cell_io::emit(result);startup.emit(state);input_mouse_runtime_cases::emit(0,runtime,backend);
        cell_io::emit(toggle.state);cell_io::emit(std::uint32_t(toggle.platform.event==input_toggle_key_cases::Calls::second));
        cell_io::emit(static_cast<std::uint32_t>(toggle.logs.size()));
        for(const auto& row:toggle.logs)cell_io::emit(row);
    }
});}
