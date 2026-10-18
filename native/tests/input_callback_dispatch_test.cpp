#include "input_callback_dispatch_cases.hpp"
#include <stdexcept>
int main(){
    auto require=[](bool ok,const char* message){if(!ok)throw std::runtime_error(message);};
    input_callback_dispatch_cases::Fixture f;f.config={1,0x7000e000,1,0,0,0x12345678,8,0};f.initialize();auto state=f.state();
    require(mco::input_callback_dispatch(state,f.platform())==0x12345678 && f.logs.size()==1 && f.logs[0][0]==2,"callback return was masked or fallback ran");
    require(static_cast<std::uint32_t>(state.callback)==0x7000e100 && state.enabled==0,"callback side effects lost");
    require(mco::input_callback_dispatch(state,f.platform())==0 && f.logs.size()==2 && f.logs.back()[0]==0,"next dispatch did not reread gate");
    f.config[3]=1;f.config[4]=0x12345680;f.config[6]=3;f.logs.clear();
    require(mco::input_callback_fallback(state,f.platform())==128 && f.logs.size()==2 && f.logs[1][0]==1,"fallback reselected callback or lost byte mask");
    require(f.logs[1][2]==0x7000e100 && f.logs[1][3]==0,"read did not follow availability mutations");
    f.config[3]=0xffffffff;f.config[4]=0xffffffff;
    require(mco::input_callback_fallback(state,f.platform())==255,"nonzero high-bit availability or byte extension changed");
    f.config[3]=0;auto platform=f.platform();platform.read=nullptr;
    require(mco::input_callback_fallback(state,platform)==0,"unused read bridge was required");
    state.callback=0x7000e000;state.enabled=0x80000000;f.config[5]=0xdeadbeef;f.config[6]=0;
    require(mco::input_callback_dispatch(state,f.platform())==0xdeadbeef,"high-bit enabled or full callback result changed");
    state.callback=0;f.config[3]=0;platform.invoke=nullptr;
    require(mco::input_callback_dispatch(state,platform)==0,"null callback did not use fallback");
}
