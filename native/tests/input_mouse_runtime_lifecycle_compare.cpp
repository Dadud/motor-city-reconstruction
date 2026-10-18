#include "input_mouse_runtime_cases.hpp"
using namespace mco;
using input_mouse_runtime_cases::Fixture;
int main(){return cell_io::run([](std::istream& input){
    Fixture f;const auto profile=cell_io::read(input),script=cell_io::read(input),seed=cell_io::read(input);
    f.backend.config={0,profile,script,seed};for(unsigned i=0;i<6;++i)f.backend.tables[i]=(seed+i)%2;
    std::array<std::uint32_t,15> words{};std::uint32_t width=640,height=480;InputMouseLifetimeState lifetime{words,width,height};
    std::array<std::byte,input_queue_image::size> globals{};std::array<std::byte,mouse_input_image::size> image{};
    WindowDispatchState window{globals,1,Fixture::sync,Fixture::dispatch,&f};
    window.store(input_queue_image::target_window,7);window.store(input_queue_image::device_window,7);window.store(input_queue_image::dispatch_synchronizer,0x12345678);
    MouseInputState mouse{window,image,0,0};std::uint32_t x=0,y=0,buttons=0,wheel=0,counter=0;
    std::array<std::uint32_t,3> ids{};InputMouseGeometryState geometry{mouse,x,y};InputMouseCallbacks callbacks{lifetime,geometry,wheel,counter,buttons,ids};
    std::uint32_t mode=0,state8=0,state9=0,diagnostic=0x7000f200,file=0,line=0;
    InputMouseStateSet setter{lifetime,mode,state8,state9,diagnostic,file,line};
    std::array<std::uint32_t,64> slots{};CleanupRegistry registry{slots};
    InputMouseRuntimeBinding binding{setter,geometry,callbacks,registry,{Fixture::external,&f},{Fixture::resolve,Fixture::state_call,&f},
        {Fixture::convert,Fixture::position,Fixture::cursor,nullptr,&f},{Fixture::context,&f}};f.binding=&binding;
    const auto count=cell_io::read(input);if(count==0 || count>256)throw std::invalid_argument("runtime step count");
    for(unsigned i=0;i<count;++i){
        const auto op=cell_io::read(input),a=cell_io::read(input),b=cell_io::read(input),c=cell_io::read(input);(void)c;
        std::uint32_t result=0;
        switch(op){
        case 0:result=input_mouse_lifetime(lifetime,binding.lifetime_platform(),0x71001400);break;
        case 1:result=input_mouse_state_set(setter,binding.state_platform(),a,b);break;
        case 2:{const std::array<std::uint32_t,6> args{0,0,0,a,b,500};input_mouse_bounds(lifetime,binding.lifetime_platform(),args);break;}
        case 3:input_mouse_set_position(geometry,binding.cursor,binding.context,a,b);break;
        case 4:result=window_message_dispatch(window,b,0x20a,a,0,0);break;
        case 5:result=input_mouse_report(callbacks);break;
        case 6:input_mouse_counter_increment(callbacks);break;
        case 7:input_mouse_counter_decrement(callbacks);break;
        case 8:cleanup_registry_run(registry,binding.cleanup_platform());break;
        case 9:cleanup_registry_register(registry,0x6efad0);break;
        default:throw std::invalid_argument("runtime operation");
        }
        input_mouse_runtime_cases::emit(result,binding,f);
    }
});}
