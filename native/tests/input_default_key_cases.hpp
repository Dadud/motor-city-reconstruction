#pragma once
#include "mco/input_default_key.hpp"
#include "mco/input_default_key_binding.hpp"
#include "input_callback_dispatch_cases.hpp"
#include "input_queue_cases.hpp"
#include "input_translation_cases.hpp"
namespace input_default_key_cases {
struct Actions {
    std::uint32_t script{};
    std::array<std::byte,1024> image{};
    mco::InputCallbackDispatchState* control{};
    std::vector<std::array<std::uint32_t,1027>> logs;
    static void invoke(mco::InputKeyActions&,std::uint32_t identity,void* user){
        auto& f=*static_cast<Actions*>(user);std::array<std::uint32_t,1027> row{};row[0]=identity;
        for(unsigned i=0;i<1024;++i)row[1+i]=std::to_integer<std::uint32_t>(f.image[i]);
        row[1025]=f.control->callback;row[1026]=f.control->enabled;f.logs.push_back(row);
        if(f.script&1){f.image[0x104+17]=std::byte{};f.image[0x104+65]=std::byte{};}
        if(f.script&2)mco::detail::write_word(f.image,4,0);
        if(f.script&4){f.image[0x204+128]=std::byte{255};mco::detail::write_word(f.image,255*4,0x7000e300);}
        if(f.script&8){f.control->callback=0;f.control->enabled=0;}
    }
    mco::InputKeyActions state(){return {image,invoke,this};}
    void emit(){
        cell_io::emit(image);cell_io::emit(control->callback);cell_io::emit(control->enabled);cell_io::emit(static_cast<std::uint32_t>(logs.size()));
        for(const auto& row:logs)cell_io::emit(row);
    }
};
inline void emit_translation(const mco::InputTranslationState& state,const input_translation_cases::Fixture& f){
    cell_io::emit(state.caps);cell_io::emit(state.escape_exits);cell_io::emit(static_cast<std::uint32_t>(f.logs.size()));
    for(const auto& row:f.logs)cell_io::emit(row);cell_io::emit(f.device);cell_io::emit(f.tables);
}
inline void compare(std::istream& input){
    const auto mode=cell_io::read(input);Actions actions;
    input_callback_dispatch_cases::Fixture dispatch;
    if(mode==0){
        const auto code=cell_io::read(input);actions.script=cell_io::read(input);actions.image=cell_io::image<1024>(input);
        dispatch.config={1,0x6f0580,1,0,0,0,0,0};dispatch.initialize();auto control=dispatch.state();actions.control=&control;auto action=actions.state();
        cell_io::emit(mco::input_key_action(action,code));actions.emit();return;
    }
    if(mode!=1)throw std::invalid_argument("default key mode");
    actions.script=cell_io::read(input);for(auto& v:dispatch.config)v=cell_io::read(input);dispatch.initialize();auto control=dispatch.state();
    input_translation_cases::Fixture tables;for(auto& v:tables.config)v=cell_io::read(input);tables.initialize();
    dispatch.callback.bind(std::span<std::byte,4>(tables.tables.data()+scan_translation_tables::callback_word,4));auto translation=tables.state();
    auto queue=queue_cases::Fixture::read(input);auto q=queue.state();actions.image=cell_io::image<1024>(input);actions.control=&control;auto action=actions.state();
    mco::InputDefaultKeyState state{control,q,translation,action};
    cell_io::emit(mco::input_default_key(state,dispatch.platform()));actions.emit();dispatch.emit();queue.emit();emit_translation(translation,tables);
}
}
