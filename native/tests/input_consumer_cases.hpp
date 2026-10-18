#pragma once
#include "input_queue_cases.hpp"
#include "input_translation_cases.hpp"
#include "mco/input_queue_pop.hpp"
#include "mco/input_queue_peek.hpp"
namespace input_consumer_cases {
struct Provider {
    mco::InputKeyQueue& queue;
    input_translation_cases::Fixture& translation;
    std::uint32_t mask,value,calls{};
    static std::span<const std::byte> get_state(mco::InputTranslationState& state,std::uint32_t kind,void* user) {
        auto& f=*static_cast<Provider*>(user);
        const auto device=input_translation_cases::Fixture::get_state(state,kind,&f.translation);
        if(++f.calls==1) {
            using namespace input_queue_image;
            if(f.mask&1)f.queue.store(read_cursor,f.value);
            if(f.mask&2)f.queue.store(capacity,2);
            if(f.mask&4)f.queue.store(synchronizer,f.value^0x11223344u);
            if(f.mask&8)f.queue.store(write_cursor,f.value&31u);
            if(f.mask&16)f.queue.store(events,0xffff5501u);
        }
        return device;
    }
    static void exit_request(mco::InputTranslationState& state,std::uint32_t code,void* user) {
        auto& f=*static_cast<Provider*>(user);
        input_translation_cases::Fixture::exit_request(state,code,&f.translation);
    }
};
inline void compare(std::istream& input,bool remove) {
    const auto mask=cell_io::read(input),value=cell_io::read(input);
    input_translation_cases::Fixture t;for(auto& v:t.config)v=cell_io::read(input);t.initialize();
    auto f=queue_cases::Fixture::read(input);auto queue=f.state();
    Provider provider{queue,t,mask,value};auto state=t.state();
    state.get_state=Provider::get_state;state.exit_request=Provider::exit_request;state.user=&provider;
    std::uint32_t outcome=0,result=0;
    try {result=remove ? mco::input_queue_pop(queue,state):mco::input_queue_peek(queue,state);}
    catch(const input_translation_cases::ExitRequested&) {outcome=1;}
    cell_io::emit(outcome);cell_io::emit(result);f.emit();
    cell_io::emit(state.caps);cell_io::emit(state.escape_exits);
    cell_io::emit(static_cast<std::uint32_t>(t.logs.size()));
    for(const auto& row:t.logs)cell_io::emit(row);
    cell_io::emit(t.device);cell_io::emit(t.tables);
}
}
