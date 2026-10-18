#include "window_dispatch_cases.hpp"
#include <stdexcept>
int main() {
    std::array<std::byte,input_queue_image::size> globals{};
    window_dispatch_cases::Fixture f{16|64,0xaabbccdd,7,0x101,{},{}};
    mco::WindowDispatchState state{globals,1,f.sync,f.invoke,&f};
    state.store(input_queue_image::dispatch_synchronizer,0x12345678);
    state.store(input_queue_image::message_handler_count,3);
    for(unsigned i=0;i<3;++i) {
        state.store(input_queue_image::message_handlers+i*8,0x100+i);
        state.store(input_queue_image::message_handlers+i*8+4,i==1 ? 0x70009100 : 0x70009000);
    }
    if(mco::window_message_dispatch(state,7,0x101,3,4,0x71003000)!=8 ||
       mco::detail::read_word(f.result,0)!=f.value || f.logs.size()!=3 ||
       f.logs[0][0]!=1 || f.logs[1][0]!=3 || f.logs[2][0]!=2 ||
       f.logs[2][1]!=(0x12345678u^f.value^0x11223344u))
        throw std::runtime_error("dispatch return, argument, or lock ordering changed");
    f.logs.clear();state.enabled=0;
    if(mco::window_message_dispatch(state,7,0x101,3,4,0)!=0 || !f.logs.empty())
        throw std::runtime_error("disabled dispatch invoked bridge");
    state.enabled=1;f.mask=2;state.store(input_queue_image::message_handler_count,129);
    if(mco::window_message_dispatch(state,7,0x101,3,4,0)!=8)
        throw std::runtime_error("table state not reloaded after entering");
    f.mask=0;state.store(input_queue_image::message_handler_count,129);
    try {mco::window_message_dispatch(state,7,0x101,3,4,0);}
    catch(const std::invalid_argument&) {return 0;}
    throw std::runtime_error("unbounded table accepted");
}
