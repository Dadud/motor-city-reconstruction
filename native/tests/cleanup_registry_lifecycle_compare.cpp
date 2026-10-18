#include "cleanup_registry_cases.hpp"
#include "input_device_lifetime_cases.hpp"
#include "mco/input_device_cleanup_binding.hpp"
int main(){return cell_io::run([](std::istream& input){
    input_device_lifetime_cases::Fixture device;
    for(auto& v:device.config)v=cell_io::read(input);device.initialize();
    std::array<std::uint32_t,7> values{};for(auto& v:values)v=cell_io::read(input);
    auto queue=queue_cases::Fixture::read(input);auto q=queue.state();
    mco::InputDeviceLifetimeState state{q,values[0],values[1],values[2],values[3],values[4],values[5],values[6]};
    cleanup_registry_cases::Fixture registry;
    if(cell_io::read(input)!=1)throw std::invalid_argument("registry lifecycle mode");
    registry.script=cell_io::read(input);cell_io::read(input);
    for(auto& v:registry.slots)v=cell_io::read(input);
    mco::InputDeviceCleanupBinding binding{registry.state,state,device.platform(),{cleanup_registry_cases::Fixture::invoke,&registry}};
    const auto count=cell_io::read(input);
    for(unsigned i=0;i<count;++i){
        const auto mode=cell_io::read(input),value=cell_io::read(input);device.temporary=nullptr;
        std::uint32_t result=0;
        if(mode==0)result=mco::input_device_initialize(state,binding.platform(),device.config[3]);
        else if(mode==1)mco::cleanup_registry_run(registry.state,binding.callbacks());
        else if(mode==2)mco::cleanup_registry_register(registry.state,value);
        else throw std::invalid_argument("registry lifecycle step");
        cell_io::emit(result);device.emit(state,queue);registry.emit();
    }
});}
