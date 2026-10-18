#include "input_console_cases.hpp"
#include "input_default_key_cases.hpp"
#include "mco/input_console_dispatch_binding.hpp"
#include "mco/input_callback_dispatch.hpp"
int main(){return cell_io::run([](std::istream& input){
    input_console_cases::Fixture f;for(auto& v:f.config)v=cell_io::read(input);f.image=cell_io::image<2168>(input);f.key=cell_io::image<16>(input);
    const auto events=cell_io::read(input);if(events>4096)throw std::invalid_argument("console lifecycle events");
    for(unsigned i=0;i<events;++i){const auto status=cell_io::read(input),count=cell_io::read(input);f.events.push_back({status,count,cell_io::image<20>(input)});}
    auto state=f.state();mco::InputDeviceCallback callback{};std::uint32_t enabled=0;mco::InputCallbackDispatchState control{callback,enabled};
    mco::InputConsoleDispatchBinding binding{state,f.platform()};
    queue_cases::Fixture queue;auto q=queue.state();input_translation_cases::Fixture tables;auto translation=tables.state();
    input_default_key_cases::Actions actions;actions.control=&control;auto action=actions.state();mco::InputDefaultKeyState key{control,q,translation,action};
    const auto count=cell_io::read(input);if(count==0 || count>4096)throw std::invalid_argument("console lifecycle count");
    for(unsigned i=0;i<count;++i){
        f.count_pointer=nullptr;const auto op=cell_io::read(input);std::uint32_t result=0;
        if(op==0)result=mco::input_console_available(state,f.platform());
        else if(op==1)result=mco::input_console_read(state,f.platform());
        else if(op==2)result=mco::input_callback_fallback(control,binding.dispatch());
        else if(op==3)result=mco::input_callback_dispatch(control,binding.dispatch());
        else if(op==4)result=mco::input_default_key(key,binding.dispatch());
        else throw std::invalid_argument("console lifecycle operation");
        cell_io::emit(result);f.emit();
    }
});}
