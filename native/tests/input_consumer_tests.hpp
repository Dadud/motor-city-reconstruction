#pragma once
#include "input_consumer_cases.hpp"
#include <stdexcept>
namespace input_consumer_tests {
inline void run(bool remove) {
    using namespace input_queue_image;
    auto require=[](bool ok,const char* message){if(!ok)throw std::runtime_error(message);};
    queue_cases::Fixture f;auto q=f.state();
    input_translation_cases::Fixture t;t.config={17,0,0,0,0,0,0,0,65,1,1};t.initialize();
    auto s=t.state();
    auto consume=[&](){return remove?mco::input_queue_pop(q,s):mco::input_queue_peek(q,s);};
    q.store(capacity,4);q.store(read_cursor,0);q.store(write_cursor,2);
    q.store(events,0x00003a01);q.store(events+4,0x00421100);
    require(consume()==0x00110042,"caps prefix did not reach stored character");
    require(s.caps==1 && q.load(read_cursor)==(remove?2u:1u),"caps consumption or usable cursor changed");
    if(!remove)require(consume()==0x00110042 && q.load(read_cursor)==1,"repeated peek consumed usable event");
    q.store(read_cursor,0);q.store(write_cursor,1);q.store(events,0x80001100);
    require(consume()==0xffff8000u,"stored character lost sign extension");
    q.store(read_cursor,0);q.store(events,0x00001101);t.tables.fill(std::byte{});
    require(consume()==0x00110000 && q.load(read_cursor)==1,"zero translation lost last scan or was retained");
    q.store(capacity,0);q.store(read_cursor,0);q.store(write_cursor,0);
    require(consume()==0,"empty queue divided by capacity");
    q.store(capacity,4);q.store(write_cursor,1);q.store(events,0x00001101);
    input_consumer_cases::Provider provider{q,t,1,2};
    s.user=&provider;s.get_state=input_consumer_cases::Provider::get_state;
    s.exit_request=input_consumer_cases::Provider::exit_request;
    t.tables.fill(std::byte{65});
    require(consume()==0x00110041 && q.load(read_cursor)==(remove?3u:2u),"provider head mutation was not reloaded");
    q.store(read_cursor,0);q.store(write_cursor,1);q.store(events,0x00000101);
    provider.mask=0;provider.calls=0;t.device.fill(std::byte{});
    t.device[direct_key_image::control_left]=std::byte{1};s.escape_exits=1;
    const auto sync_calls=f.logs.size();bool exited=false;
    try {consume();}catch(const input_translation_cases::ExitRequested&){exited=true;}
    require(exited && q.load(read_cursor)==0 && f.logs.size()==sync_calls+1,"exit advanced queue or performed leave");
}
}
