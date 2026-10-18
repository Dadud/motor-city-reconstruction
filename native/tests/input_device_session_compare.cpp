#include "input_device_lifetime_cases.hpp"
#include "input_translation_cases.hpp"
#include "mco/input_device_lifetime_access.hpp"
#include "mco/input_translation_device_binding.hpp"
#include "mco/input_key_down.hpp"
#include "mco/input_character.hpp"
#include "mco/input_queue_pop.hpp"
#include "mco/input_queue_peek.hpp"
#include "input_device_session_cases.hpp"
using input_device_session_cases::Acquisition;

int main(){return cell_io::run([](std::istream& input){
    input_device_lifetime_cases::Fixture lifetime;for(auto& v:lifetime.config)v=cell_io::read(input);lifetime.initialize();
    std::array<std::uint32_t,7> values;for(auto& v:values)v=cell_io::read(input);
    auto queue=queue_cases::Fixture::read(input);auto q=queue.state();
    mco::InputDeviceLifetimeState state{q,values[0],values[1],values[2],values[3],values[4],values[5],values[6]};
    Acquisition acquisition{lifetime,state};for(auto& v:acquisition.config)v=cell_io::read(input);acquisition.initialize();
    input_translation_cases::Fixture tables;for(auto& v:tables.config)v=cell_io::read(input);tables.initialize();
    // The supplied 620-byte lookup window includes the callback global in
    // its mapped tail. Lifetime reset follows table reset in the oracle.
    mco::input_device_bind_callback_table(state,tables.tables);
    auto translation=tables.state();
    std::array<std::uint32_t,4> shadow{};
    mco::InputDeviceAccess views{shadow[0],shadow[1],acquisition.keyboard,acquisition.information,shadow[2],shadow[3],Acquisition::resolve,nullptr,nullptr,&acquisition};
    auto access=mco::input_device_access_from_lifetime(state,views);
    mco::InputTranslationDeviceBinding binding{access,input_translation_cases::Fixture::exit_request,&tables};binding.bind(translation);
    const auto count=cell_io::read(input);if(count==0 || count>4096)throw std::invalid_argument("device session count");
    for(unsigned i=0;i<count;++i){
        const auto op=cell_io::read(input),a=cell_io::read(input),b=cell_io::read(input),c=cell_io::read(input),d=cell_io::read(input),e=cell_io::read(input);
        lifetime.temporary=nullptr;std::uint32_t result=0;
        if(op==0)result=mco::input_device_initialize(state,lifetime.platform(),lifetime.config[3]);
        else if(op==1){const auto image=mco::input_device_state(access,a);result=image.empty()?0u:0xb36460u;}
        else if(op==2)mco::input_device_cleanup(state,lifetime.platform());
        else if(op==3)mco::input_device_shutdown(state,lifetime.platform());
        else if(op==4)result=mco::input_key_down(q,queue.remap,a,b,c,d,e);
        else if(op==5)result=mco::input_character(q,a,b,c,d,e);
        else if(op==6)result=mco::input_queue_peek(q,translation);
        else if(op==7)result=mco::input_queue_pop(q,translation);
        else if(op==8)result=mco::input_scan_translate(translation,a,b);
        else if(op==9)result=mco::input_device_set_state(state,lifetime.platform(),a,b);
        else throw std::invalid_argument("device session operation");
        cell_io::emit(result);lifetime.emit(state,queue);acquisition.emit(translation,tables);
    }
});}
