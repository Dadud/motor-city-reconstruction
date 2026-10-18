#include "mco/input_mouse_runtime_binding.hpp"
#include "mco/window_message_dispatch.hpp"
#include "input_mouse_lifetime_cases.hpp"
#include <algorithm>
namespace {
using namespace mco;
struct Fixture {
    input_mouse_lifetime_cases::Fixture backend;
    std::vector<std::array<std::uint32_t,11>> events;
    InputMouseRuntimeBinding* binding{};
    unsigned cooperative{},queries{};
    void event(std::uint32_t code,std::initializer_list<std::uint32_t> args){
        std::array<std::uint32_t,11> row{};row[0]=code;row[2]=0xffffffff;row[4]=static_cast<std::uint32_t>(args.size());
        unsigned i=5;for(auto a:args)row[i++]=a;events.push_back(row);
    }
    static std::uint32_t external(InputMouseLifetimeState& s,std::uint32_t code,std::uint32_t id,
        std::span<const std::uint32_t> args,std::uint32_t slot,std::span<std::uint32_t> out,void* user){
        auto& f=*static_cast<Fixture*>(user);
        auto result=input_mouse_lifetime_cases::Fixture::invoke(s,code,id,args,slot,out,&f.backend);
        std::array<std::uint32_t,11> row{};std::copy_n(f.backend.logs.back().begin(),11,row.begin());f.events.push_back(row);
        if(code==0x34)result=f.backend.config[1]==6 && f.cooperative++%2==0?0x80004005:0;
        return result;
    }
    static std::uint32_t resolve(InputMouseStateSet&,std::uint32_t id,void* user){
        auto& f=*static_cast<Fixture*>(user);const auto i=(id-0x71001000)/256;
        if(i>=6)throw std::invalid_argument("runtime COM identity");return 0x71006000+i*512+f.backend.tables[i]*256;
    }
    static std::uint32_t state_call(InputMouseStateSet& s,std::uint32_t code,std::uint32_t,std::uint32_t id,std::span<const std::uint32_t> args,void* u){
        return external(s.lifetime,code,id,args,0,{},u);
    }
    static void sync(WindowDispatchState&,bool entering,std::uint32_t id,void* u){static_cast<Fixture*>(u)->event(entering?0x83b270:0x83b274,{id});}
    static std::uint32_t convert(std::uint32_t window,std::uint32_t& x,std::uint32_t& y,void* u){
        auto& f=*static_cast<Fixture*>(u);f.event(0x83b45c,{window,x,y});x+=100;y+=200;return f.backend.config[1]!=7;
    }
    static void position(std::uint32_t x,std::uint32_t y,void* u){static_cast<Fixture*>(u)->event(0x83b384,{x,y});}
    static void cursor(std::uint32_t id,void* u){static_cast<Fixture*>(u)->event(0x83b434,{id});}
    static std::uint32_t context(InputMouseGeometryState&,std::uint32_t code,std::uint32_t arg,void* u){
        auto& f=*static_cast<Fixture*>(u);
        if(code==0x6be930 || code==0x8c4938)f.event(code,{arg});else f.event(code,{});
        return code==0x6be930?(f.backend.config[3]+f.queries++)%2:0;
    }
    static std::uint32_t dispatch(WindowDispatchState&,std::uint32_t handler,std::uint32_t owner,std::uint32_t window,std::uint32_t,std::uint32_t wparam,std::uint32_t,std::uint32_t,void* u){
        auto& f=*static_cast<Fixture*>(u);if(handler!=0x6efa60)throw std::invalid_argument("runtime mouse handler");
        return input_mouse_wheel(f.binding->callbacks,owner,window,wparam);
    }
};
}
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
        cell_io::emit(result);cell_io::emit(words);cell_io::emit(width);cell_io::emit(height);
        cell_io::emit(mouse.enabled);cell_io::emit(mouse.button_callback);for(unsigned j=0;j<7;++j)cell_io::emit(mouse.load(j*4));
        cell_io::emit(x);cell_io::emit(y);cell_io::emit(buttons);cell_io::emit(wheel);cell_io::emit(counter);cell_io::emit(ids);cell_io::emit(window.load(input_queue_image::target_window));
        cell_io::emit(mode);cell_io::emit(state8);cell_io::emit(state9);cell_io::emit(diagnostic);cell_io::emit(file);cell_io::emit(line);
        cell_io::emit(globals);cell_io::emit(slots);cell_io::emit(f.backend.tables);cell_io::emit(static_cast<std::uint32_t>(f.events.size()));
        for(const auto& row:f.events)cell_io::emit(row);f.events.clear();
    }
});}
