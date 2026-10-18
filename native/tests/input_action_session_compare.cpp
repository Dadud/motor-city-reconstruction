#include "input_device_session_cases.hpp"
#include "input_default_key_cases.hpp"
#include "mco/input_callback_dispatch.hpp"
#include "mco/input_character.hpp"
#include "mco/input_key_down.hpp"
int main(){return cell_io::run([](std::istream& input){
    input_device_lifetime_cases::Fixture lifetime;for(auto& v:lifetime.config)v=cell_io::read(input);lifetime.initialize();
    std::array<std::uint32_t,7> values;for(auto& v:values)v=cell_io::read(input);
    auto queue=queue_cases::Fixture::read(input);auto q=queue.state();
    mco::InputDeviceLifetimeState state{q,values[0],values[1],values[2],values[3],values[4],values[5],values[6]};
    input_device_session_cases::Acquisition acquisition{lifetime,state};for(auto& v:acquisition.config)v=cell_io::read(input);acquisition.initialize();
    input_translation_cases::Fixture tables;for(auto& v:tables.config)v=cell_io::read(input);tables.initialize();mco::input_device_bind_callback_table(state,tables.tables);auto translation=tables.state();
    std::array<std::uint32_t,4> shadow{};
    mco::InputDeviceAccess views{shadow[0],shadow[1],acquisition.keyboard,acquisition.information,shadow[2],shadow[3],input_device_session_cases::Acquisition::resolve,nullptr,nullptr,&acquisition};
    auto access=mco::input_device_access_from_lifetime(state,views);mco::InputTranslationDeviceBinding binding{access,input_translation_cases::Fixture::exit_request,&tables};binding.bind(translation);
    input_callback_dispatch_cases::Fixture dispatch;for(auto& v:dispatch.config)v=cell_io::read(input);dispatch.initialize();
    dispatch.callback.bind(std::span<std::byte,4>(tables.tables.data()+scan_translation_tables::callback_word,4));mco::InputCallbackDispatchState control{state.callback,dispatch.enabled};
    input_default_key_cases::Actions actions;actions.script=cell_io::read(input);actions.image=cell_io::image<1024>(input);actions.control=&control;auto action=actions.state();
    mco::InputDefaultKeyState key{control,q,translation,action};mco::InputDefaultKeyBinding default_binding{key,dispatch.platform()};
    const auto count=cell_io::read(input);if(count==0 || count>4096)throw std::invalid_argument("action session count");
    for(unsigned i=0;i<count;++i){
        const auto op=cell_io::read(input),a=cell_io::read(input),b=cell_io::read(input),c=cell_io::read(input),d=cell_io::read(input),e=cell_io::read(input);
        lifetime.temporary=nullptr;std::uint32_t result=0;
        if(op==0)result=mco::input_device_initialize(state,lifetime.platform(),lifetime.config[3]);
        else if(op==1){const auto image=mco::input_device_state(access,a);result=image.empty()?0u:0xb36460u;}
        else if(op==2)mco::input_device_cleanup(state,lifetime.platform());
        else if(op==3)mco::input_device_shutdown(state,lifetime.platform());
        else if(op==4)result=mco::input_key_down(q,queue.remap,a,b,c,d,e);
        else if(op==5)result=mco::input_character(q,a,b,c,d,e);
        else if(op==9)result=mco::input_device_set_state(state,lifetime.platform(),a,b);
        else if(op==10)result=mco::input_callback_dispatch(control,default_binding.platform());
        else throw std::invalid_argument("action session operation");
        cell_io::emit(result);lifetime.emit(state,queue);acquisition.emit(translation,tables);actions.emit();dispatch.emit();
    }
});}
