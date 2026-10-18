#include "input_callback_dispatch_cases.hpp"
#include "input_queue_cases.hpp"
#include "mco/input_device_lifetime.hpp"
int main(){return cell_io::run([](std::istream& input){
    input_callback_dispatch_cases::Fixture f;for(auto& v:f.config)v=cell_io::read(input);f.initialize();
    queue_cases::Fixture queue;auto q=queue.state();std::array<std::uint32_t,4> globals{};
    mco::InputDeviceLifetimeState lifetime{q,globals[0],globals[1],0,0,f.callback,globals[2],globals[3]};
    mco::InputCallbackDispatchState state{lifetime.callback,f.enabled};
    const auto count=cell_io::read(input);if(count==0 || count>4096)throw std::invalid_argument("callback lifecycle count");
    for(unsigned i=0;i<count;++i){
        const auto op=cell_io::read(input),value=cell_io::read(input);std::uint32_t result=0;
        if(op==0)result=mco::input_callback_dispatch(state,f.platform());
        else if(op==1)result=mco::input_callback_fallback(state,f.platform());
        else if(op==2)result=mco::input_device_set_state(lifetime,{},10,value);
        else throw std::invalid_argument("callback lifecycle operation");
        cell_io::emit(result);f.emit();
    }
});}
