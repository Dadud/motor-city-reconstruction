#include "input_default_key_cases.hpp"
#include "mco/input_callback_dispatch.hpp"
#include <stdexcept>
int main(){
    using mco::detail::write_word;
    auto require=[](bool ok,const char* message){if(!ok)throw std::runtime_error(message);};
    input_callback_dispatch_cases::Fixture dispatch;dispatch.config={1,0x6f0580,1,1,0x12345680,0xabcdef01,0,0};dispatch.initialize();auto control=dispatch.state();
    input_default_key_cases::Actions f;f.control=&control;auto action=f.state();
    f.image[0x104+65]=std::byte{1};write_word(f.image,4,0x7000e200);f.script=1;
    require(mco::input_key_action(action,65)==0 && f.logs.size()==1,"mapped action not consumed");
    require(mco::input_key_action(action,65)==65 && f.logs.size()==1,"map mutation not visible to next call");
    f.image.fill(std::byte{});f.image[0x104+17]=std::byte{1};
    require(mco::input_key_action(action,17)==0 && f.logs.size()==1,"null handler did not consume mapped code");
    f.script=0;f.image.fill(std::byte{});f.image[0]=std::byte{1};write_word(f.image,4,0x7000e200);
    require(mco::input_key_action(action,0xfffffefc)==0,"mapped negative index changed");
    f.image[0]=std::byte{};require(mco::input_key_action(action,0xfffffefc)==0xfffffefc,"unmapped negative result was normalized");
    f.image.fill(std::byte{});write_word(f.image,65*4,0x7000e200);
    require(mco::input_key_action(action,1)==0 && mco::input_key_action(action,2)==2,"handler/map overlap was separated");
    require(mco::input_key_action(action,0x10000)==0x10000 && mco::input_key_action(action,0x7fffffff)==0x7fffffff,"positive passthrough changed");
    queue_cases::Fixture queue;auto q=queue.state();q.store(input_queue_image::capacity,4);q.store(input_queue_image::write_cursor,1);
    write_word(queue.globals,input_queue_image::events,0x8000fe00);
    input_translation_cases::Fixture tables;tables.config={17,0,0,128,0,0,0,73,65,1,1};tables.initialize();auto translation=tables.state();
    f.image.fill(std::byte{});mco::InputDefaultKeyState key{control,q,translation,action};
    require(mco::input_default_key(key,dispatch.platform())==0x8000 && q.load(input_queue_image::read_cursor)==1,"queue scan/sign prefix was not truncated");
    control.enabled=0;q.store(input_queue_image::read_cursor,0);q.store(input_queue_image::capacity,0);const auto locks=queue.logs.size();
    require(mco::input_default_key(key,dispatch.platform())==128 && queue.logs.size()==locks && q.load(input_queue_image::read_cursor)==0,"disabled callback touched queue or skipped fallback mask");
    control.enabled=1;control.callback=0x6f0580;q.store(input_queue_image::capacity,4);write_word(queue.globals,input_queue_image::events,0x00411100);
    f.image[0x104+65]=std::byte{65};write_word(f.image,65*4,0x7000e200);mco::InputDefaultKeyBinding binding{key,dispatch.platform()};
    require(mco::input_callback_dispatch(control,binding.platform())==0 && q.load(input_queue_image::read_cursor)==1,"dispatcher did not invoke recovered default callback");
    control.callback=0x7000e000;require(mco::input_callback_dispatch(control,binding.platform())==0xabcdef01,"other callback context not forwarded");
}
