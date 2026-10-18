#include "cell_io.hpp"
#include "mco/combined_input_binding.hpp"
#include "mco/window_keyboard_layout_binding.hpp"
#include "mco/window_message_dispatch.hpp"
#include "mco/input_key_query.hpp"
#include "mco/input_device_lifetime_access.hpp"
#include "mco/input_shared_tables.hpp"
#include "diagnostic_runtime_cases.hpp"
#include <vector>
using namespace mco;
namespace {
struct Backend {
    std::array<std::uint32_t,2> profiles{};
    std::vector<std::uint32_t> events;
    std::uint32_t toggle_state{},toggle_calls{};
    InputMouseRuntimeBinding* mouse{};
    std::uint32_t com(unsigned domain,std::uint32_t code,std::uint32_t id,std::uint32_t slot,std::span<std::uint32_t> out){
        const auto base=0x71001000u+domain*0x2000;
        if(id && (id<base || id>=base+0x600 || (id&255)))throw std::invalid_argument("combined COM namespace");
        const bool create=slot==1;
        if(create || id){events.insert(events.end(),{domain,create?0x101u:code,id});}
        if(slot && out.empty())throw std::invalid_argument("combined output slot");
        if(slot==1)out[0]=base;
        if(slot==2)out[0]=base+0x400;
        if(slot==3)out[0]=base+0x200;
        unsigned stage=create?1:code==0xc?2:code==0?3:code==0x2c?4:(code==0x18 || code==0x34)?5:0;
        return stage && profiles[domain]==stage?0x80004005u:0;
    }
    static std::uint32_t keyboard(InputDeviceLifetimeState&,std::uint32_t code,std::uint32_t id,std::span<const std::uint32_t>,std::uint32_t slot,std::uint32_t* out,void* u){
        auto& b=*static_cast<Backend*>(u);
        if(code==device_lifetime_call::create_sync)return 0x12345678;
        if(code==device_lifetime_call::module_handle)return 0x400000;
        if(code==device_lifetime_call::diagnostic)return 0;
        return b.com(1,code,id,slot,out?std::span<std::uint32_t>(out,1):std::span<std::uint32_t>{});
    }
    static std::uint32_t external(InputMouseLifetimeState&,std::uint32_t code,std::uint32_t id,std::span<const std::uint32_t>,std::uint32_t slot,std::span<std::uint32_t> out,void* u){
        auto& b=*static_cast<Backend*>(u);
        if(code==mouse_lifetime_call::module)return 0x400000;
        if(code==mouse_lifetime_call::cursor){out[0]=100;out[1]=200;return 1;}
        if(code==mouse_lifetime_call::client){out[0]+=17;out[1]+=31;return 1;}
        return b.com(0,code,id,slot,out);
    }
    static std::uint32_t resolve(InputMouseStateSet&,std::uint32_t id,void*){
        if(id<0x71001000 || id>=0x71001600 || (id&255))throw std::invalid_argument("combined mouse identity");
        return 0x71006000+id-0x71001000;
    }
    static std::uint32_t state(InputMouseStateSet& s,std::uint32_t code,std::uint32_t,std::uint32_t id,std::span<const std::uint32_t> args,void* u){return external(s.lifetime,code,id,args,0,{},u);}
    static void syncq(InputKeyQueue&,bool,std::uint32_t,void*){}
    static void syncw(WindowDispatchState&,bool,std::uint32_t,void*){}
    static std::uint32_t convert(std::uint32_t,std::uint32_t& x,std::uint32_t& y,void*){x+=100;y+=200;return 1;}
    static void position(std::uint32_t,std::uint32_t,void*){}
    static void cursor(std::uint32_t,void*){}
    static std::uint32_t context(InputMouseGeometryState&,std::uint32_t,std::uint32_t,void*){return 0;}
    static std::uint32_t dispatch(WindowDispatchState&,std::uint32_t handler,std::uint32_t owner,std::uint32_t window,std::uint32_t,std::uint32_t wp,std::uint32_t,std::uint32_t,void* u){
        auto& b=*static_cast<Backend*>(u);if(handler!=0x6efa60)throw std::invalid_argument("combined handler");return input_mouse_wheel(b.mouse->callbacks,owner,window,wp);
    }
    static std::uint32_t key_type(InputKeyQueue&,std::uint32_t kind,void*){return kind==0?7:0xd01;}
    static std::uint32_t toggle_query(std::uint32_t,void* u){auto& b=*static_cast<Backend*>(u);++b.toggle_calls;return b.toggle_state;}
    static void toggle_event(std::uint32_t,std::uint32_t,std::uint32_t flags,std::uint32_t,void* u){auto& b=*static_cast<Backend*>(u);++b.toggle_calls;if(flags&2)b.toggle_state^=1;}
    static bool nonempty(std::uint32_t id,void*){return id!=0x71005000;}
    static std::uint32_t startup(StartupState& s,std::uint32_t id,std::span<const std::uint32_t>,void*){
        if(id==0x6bda50)s.at(StartupGlobal::diagnostic_callback)=0x7000e900;
        if(id==0x6d0f20)return 0;
        if(id==0x6d0820)return 1;
        if(id==0x6d0cd0){s.at(StartupGlobal::graphics_ready)=1;return 1;}
        return 0x11110000u+(id&65535u);
    }
};
}
int main(){return cell_io::run([](std::istream& in){
    Backend b;b.profiles[0]=cell_io::read(in);b.profiles[1]=cell_io::read(in);b.toggle_state=cell_io::read(in);
    std::array<std::byte,input_queue_image::size> globals{};std::array<std::byte,256> keys{};std::array<std::byte,128> other_remap{};
    InputKeyQueue queue{globals,keys,Backend::syncq,&b};queue.store(input_queue_image::target_window,7);queue.store(input_queue_image::device_window,7);queue.store(input_queue_image::dispatch_synchronizer,0x12345678);
    std::array<std::uint32_t,15> startup_words{0,0x1234,0x5678,0,1,0x7777,0,0xa5,0,640,480,32,1,2,0};
    StartupState startup{queue,startup_words};using G=StartupGlobal;
    std::array<std::uint32_t,15> words{};InputMouseLifetimeState lifetime{words,startup.at(G::width),startup.at(G::height)};
    WindowDispatchState window{globals,1,Backend::syncw,Backend::dispatch,&b};
    std::array<std::byte,mouse_input_image::size> image{};MouseInputState mouse{window,image,0,0};
    InputSharedTables shared_tables;
    auto tables=shared_tables.image();
    for(unsigned i=0;i<tables.size();++i)tables[i]=std::byte((i*29)&255);tables[488+17]=std::byte{42};tables[488+42]=std::byte{54};
    auto& mode=shared_tables.mouse_mode();auto& state8=shared_tables.mouse_state8();auto& state9=shared_tables.mouse_state9();
    std::uint32_t x=0,y=0,wheel=0,counter=0,buttons=0;
    InputMouseGeometryState geometry{mouse,x,y};std::array<std::uint32_t,3> callbacks{};InputMouseCallbacks cb{lifetime,geometry,wheel,counter,buttons,callbacks};
    InputMouseStateSet setter{lifetime,mode,state8,state9,startup.at(G::diagnostic_callback),startup.at(G::diagnostic_file),startup.at(G::diagnostic_line)};
    std::array<std::uint32_t,64> slots{};CleanupRegistry registry{slots};
    InputMouseRuntimeBinding runtime{setter,geometry,cb,registry,{Backend::external,&b},{Backend::resolve,Backend::state,&b},{Backend::convert,Backend::position,Backend::cursor,nullptr,&b},{Backend::context,&b}};b.mouse=&runtime;
    std::uint32_t iface=0,device=0;InputDeviceLifetimeState keyboard{queue,iface,device,0,0,0,startup.at(G::diagnostic_file),startup.at(G::diagnostic_line)};
    input_device_bind_callback_table(keyboard,tables);
    InputKeyboardLayoutPlatform layout{Backend::key_type,&b};InputToggleKeyPlatform toggle{Backend::toggle_query,Backend::toggle_event,&b};
    CombinedInputBinding binding{runtime,keyboard,{Backend::keyboard,&b},layout,toggle,{Backend::startup,Backend::nonempty,&b}};
    DiagnosticRuntime diagnostics;
    for(unsigned i=0;i<diagnostics.words.size();++i)diagnostics.words[i]=i*7919;
    diagnostics.words[(0x8c4938-0x8c4730)/4]=0x7000f100;
    diagnostic_runtime_cases::Boundary diagnostic_boundary{b.toggle_state,{}};
    binding.diagnostics=&diagnostics;
    binding.diagnostic_platform={diagnostic_runtime_cases::env,diagnostic_runtime_cases::config,&diagnostic_boundary};
    std::array<std::byte,512> latches{};auto count=cell_io::read(in);if(!count || count>256)throw std::invalid_argument("combined step count");
    for(unsigned i=0;i<count;++i){
        auto op=cell_io::read(in),a=cell_io::read(in),c=cell_io::read(in),d=cell_io::read(in),e=cell_io::read(in),g=cell_io::read(in);std::uint32_t result=0;
        switch(op){
        case 0:startup_initialize(startup,binding.startup_platform());break;
        case 1:case 2:result=window_keyboard_layout_binding(queue,tables,other_remap,op==1?0x584450:0x584610,a,c,d,e,g);break;
        case 3:cleanup_registry_run(registry,binding.cleanup_platform());break;
        case 4:result=input_key_query(std::span<const std::byte,128>(keys.data(),128),latches,a,c);break;
        case 5:result=window_message_dispatch(window,c,0x20a,a,0,0);break;
        case 6:input_mouse_set_position(geometry,runtime.cursor,runtime.context,a,c);break;
        case 7:result=input_mouse_report(cb);break;
        case 8:input_mouse_counter_increment(cb);break;
        case 9:startup.at(G::width)=a;startup.at(G::height)=c;break;
        case 10:startup.at(G::graphics_ready)=a;break;
        default:throw std::invalid_argument("combined operation");
        }
        cell_io::emit(result);cell_io::emit(startup_words);cell_io::emit(words);cell_io::emit(lifetime.width);cell_io::emit(lifetime.height);
        cell_io::emit(mouse.enabled);cell_io::emit(mouse.button_callback);for(unsigned j=0;j<7;++j)cell_io::emit(mouse.load(j*4));
        cell_io::emit(x);cell_io::emit(y);cell_io::emit(buttons);cell_io::emit(wheel);cell_io::emit(counter);cell_io::emit(callbacks);cell_io::emit(queue.load(input_queue_image::target_window));
        cell_io::emit(mode);cell_io::emit(state8);cell_io::emit(state9);cell_io::emit(startup.at(G::diagnostic_callback));cell_io::emit(startup.at(G::diagnostic_file));cell_io::emit(startup.at(G::diagnostic_line));
        cell_io::emit(iface);cell_io::emit(device);cell_io::emit(keyboard.initialized);cell_io::emit(keyboard.cleanup_registered);cell_io::emit(static_cast<std::uint32_t>(keyboard.callback));cell_io::emit(startup.at(G::diagnostic_file));cell_io::emit(startup.at(G::diagnostic_line));
        cell_io::emit(globals);cell_io::emit(keys);for(auto v:tables)cell_io::emit(static_cast<std::uint32_t>(v));cell_io::emit(latches);cell_io::emit(slots);cell_io::emit(b.toggle_state);cell_io::emit(b.toggle_calls);cell_io::emit(static_cast<std::uint32_t>(b.events.size()/3));for(auto v:b.events)cell_io::emit(v);
        cell_io::emit(diagnostics.initialized);cell_io::emit(diagnostics.words);
        cell_io::emit(static_cast<std::uint32_t>(diagnostic_boundary.logs.size()));
        for(auto value:diagnostic_boundary.logs)cell_io::emit(value);
    }
});}
