#include "input_default_key_cases.hpp"
#include "mco/input_callback_dispatch.hpp"
#include "mco/input_character.hpp"
#include "mco/input_key_down.hpp"
int main(){return cell_io::run([](std::istream& input){
    input_default_key_cases::Actions actions;actions.script=cell_io::read(input);
    input_callback_dispatch_cases::Fixture dispatch;for(auto& v:dispatch.config)v=cell_io::read(input);dispatch.initialize();auto control=dispatch.state();
    input_translation_cases::Fixture tables;for(auto& v:tables.config)v=cell_io::read(input);tables.initialize();
    dispatch.callback.bind(std::span<std::byte,4>(tables.tables.data()+scan_translation_tables::callback_word,4));auto translation=tables.state();
    auto queue=queue_cases::Fixture::read(input);auto q=queue.state();actions.image=cell_io::image<1024>(input);actions.control=&control;auto action=actions.state();
    mco::InputDefaultKeyState state{control,q,translation,action};mco::InputDefaultKeyBinding binding{state,dispatch.platform()};
    const auto count=cell_io::read(input);if(count==0 || count>4096)throw std::invalid_argument("default key lifecycle count");
    for(unsigned i=0;i<count;++i){
        const auto op=cell_io::read(input),a=cell_io::read(input),b=cell_io::read(input),c=cell_io::read(input),d=cell_io::read(input),e=cell_io::read(input);std::uint32_t result=0;
        if(op==0)result=mco::input_character(q,a,b,c,d,e);
        else if(op==1)result=mco::input_callback_dispatch(control,binding.platform());
        else if(op==2)result=mco::input_key_down(q,queue.remap,a,b,c,d,e);
        else if(op==3)result=mco::input_default_key(state,dispatch.platform());
        else if(op==4)result=mco::input_key_action(action,a);
        else throw std::invalid_argument("default key lifecycle operation");
        cell_io::emit(result);actions.emit();dispatch.emit();queue.emit();input_default_key_cases::emit_translation(translation,tables);
    }
});}
