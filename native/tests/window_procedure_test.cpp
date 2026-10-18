#include "window_dispatch_cases.hpp"
#include <stdexcept>
int main() {
    for(unsigned scenario=0;scenario<6;++scenario) {
        std::array<std::byte,input_queue_image::size> globals{};
        window_dispatch_cases::Fixture f{64,0xaabbccdd,7,0x100,{},{}};
        mco::WindowDispatchState state{globals,1,f.sync,f.invoke,&f};
        state.store(input_queue_image::dispatch_synchronizer,1234);
        state.store(input_queue_image::message_handler_count,1);
        state.store(input_queue_image::message_handlers,0x100);
        state.store(input_queue_image::message_handlers+4,0x70009000);
        const mco::WindowProcedureBridge bridge{f.window_invoke,f.default_procedure,&f};
        if(scenario==1) f.mask=0;
        if(scenario==2) f.retval=0;
        if(scenario==3) state.enabled=0;
        if(scenario==5) f.mask=64|128;
        const auto message=scenario==4 ? 0x101u : 0x100u;
        const auto result=mco::window_procedure(state,bridge,7,message,3,4);
        const auto expected=scenario==0 ? f.value : scenario==1 ? 0u :
            scenario==5 ? f.value^0x55aa55aau : f.value^0x87654321u;
        if(result!=expected) throw std::runtime_error("handled/local/default result changed");
        if(scenario==3) {
            if(f.logs.size()!=1 || f.logs[0][0]!=4)
                throw std::runtime_error("disabled procedure acquired lock");
        } else if(scenario==2 || scenario==4) {
            if(f.logs.back()[0]!=4 || f.logs[f.logs.size()-2][0]!=2)
                throw std::runtime_error("default procedure ran before leave");
        } else if(f.logs.back()[0]!=2)
            throw std::runtime_error("handled procedure invoked default");
    }
}
