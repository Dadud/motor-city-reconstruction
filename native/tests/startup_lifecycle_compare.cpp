#include "startup_initialize_cases.hpp"
#include "input_device_lifetime_cases.hpp"
#include "input_keyboard_layout_cases.hpp"
#include "cleanup_registry_cases.hpp"
#include "mco/startup_input_binding.hpp"
#include "mco/input_device_cleanup_binding.hpp"
#include "mco/input_device_lifetime_access.hpp"
#include "mco/window_keyboard_layout_binding.hpp"
#include "mco/input_key_query.hpp"
#ifdef MCO_STARTUP_TOGGLE
#include "startup_toggle_cases.hpp"
#endif
int main(){return cell_io::run([](std::istream& input){
    startup_initialize_cases::Fixture startup;for(auto& v:startup.config)v=cell_io::read(input);for(auto& v:startup.values)v=cell_io::read(input);
    input_device_lifetime_cases::Fixture lifetime;for(auto& v:lifetime.config)v=cell_io::read(input);lifetime.initialize();
    std::array<std::uint32_t,7> values{};for(auto& v:values)v=cell_io::read(input);auto queue=queue_cases::Fixture::read(input);auto q=queue.state();
    mco::StartupState state{q,startup.values};using G=mco::StartupGlobal;
    mco::InputDeviceLifetimeState device{q,values[0],values[1],values[2],values[3],values[4],state.at(G::diagnostic_file),state.at(G::diagnostic_line)};
    input_keyboard_layout_cases::Fixture layout;for(auto& v:layout.config)v=cell_io::read(input);layout.tables=cell_io::image<scan_translation_tables::size>(input);mco::input_device_bind_callback_table(device,layout.tables);
    cleanup_registry_cases::Fixture registry;
    if(cell_io::read(input)!=1)throw std::invalid_argument("startup registry mode");registry.script=cell_io::read(input);cell_io::read(input);for(auto& v:registry.slots)v=cell_io::read(input);
    auto latches=cell_io::image<512>(input);
    mco::InputDeviceCleanupBinding cleanup{registry.state,device,lifetime.platform(),{cleanup_registry_cases::Fixture::invoke,&registry}};
    mco::StartupInputBinding binding{device,cleanup.platform(),layout.platform,startup.platform(),lifetime.config[3]};
    auto startup_platform=binding.platform();
#ifdef MCO_STARTUP_TOGGLE
    startup_toggle_cases::Fixture toggle{device};
    toggle.state=cell_io::read(input);toggle.script=cell_io::read(input);
    mco::StartupToggleBinding toggle_binding{toggle.platform,binding.incoming_temporary,startup_platform};
    startup_platform=toggle_binding.platform();
#endif
    const auto count=cell_io::read(input);if(count==0 || count>4096)throw std::invalid_argument("startup session count");
    for(unsigned i=0;i<count;++i){
        const auto op=cell_io::read(input),a=cell_io::read(input),b=cell_io::read(input),c=cell_io::read(input),d=cell_io::read(input),e=cell_io::read(input);lifetime.temporary=nullptr;std::uint32_t result=0;
        if(op==0)mco::startup_initialize(state,startup_platform);
        else if(op==1)result=mco::window_keyboard_layout_binding(q,layout.tables,queue.remap,0x584450,a,b,c,d,e);
        else if(op==2)result=mco::window_keyboard_layout_binding(q,layout.tables,queue.remap,0x584610,a,b,c,d,e);
        else if(op==3)mco::cleanup_registry_run(registry.state,cleanup.callbacks());
        else if(op==4)result=mco::input_key_query(std::span<const std::byte,128>(queue.keys.data(),128),latches,a,b);
        else if(op==5)mco::cleanup_registry_register(registry.state,a);
        else if(op==6)state.at(G::graphics_ready)=a;
        else throw std::invalid_argument("startup session step");
        cell_io::emit(result);startup.emit(state);lifetime.emit(device,queue);layout.emit();registry.emit();cell_io::emit(latches);
#ifdef MCO_STARTUP_TOGGLE
        toggle.emit();
#endif
    }
});}
